import logging
import math
from typing import Literal

logger = logging.getLogger(__name__)

from rag._ragas_compat import ensure_ragas_importable

ensure_ragas_importable()

from rag.generation import NO_ANSWER_PHRASE, NO_CITATION_FALLBACK

# Matches the offline RAGAS eval harness's faithfulness bar (rag/evaluator.py).
FAITHFULNESS_ABSTAIN_THRESHOLD = 0.85
FAITHFULNESS_LOW_THRESHOLD = 0.5

ABSTENTION_MESSAGE = "I don't have enough context to answer this reliably"

Confidence = Literal["high", "medium", "low"]

# Answers that are already a refusal (Phase 3's citation-grounding fallback, or the
# system prompt's own "no answer" phrase) carry no claims to fact-check — scoring
# them would just burn an extra LLM call for a meaningless number.
_REFUSAL_MESSAGES = {NO_ANSWER_PHRASE, NO_CITATION_FALLBACK}


def score_faithfulness(question: str, answer: str, contexts: list[str]) -> float:
    """Score how faithful `answer` is to `contexts` using RAGAS's faithfulness
    metric, via the same evaluate()-based call the offline eval harness
    (rag/evaluator.py) uses — just for a single row instead of a batch."""
    from datasets import Dataset
    from ragas import evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import faithfulness
    from ragas.run_config import RunConfig

    from rag.embedding import embedder
    from rag.generation import _get_llm

    dataset = Dataset.from_dict({
        "question": [question],
        "answer": [answer],
        "contexts": [contexts],
        "ground_truth": [""],  # unused by faithfulness, but evaluate()'s Dataset schema expects the column
    })

    llm_wrapper = LangchainLLMWrapper(_get_llm())
    emb_wrapper = LangchainEmbeddingsWrapper(embedder)

    # Faithfulness scoring itself makes further LLM calls (claim decomposition,
    # then per-claim verification against context) on top of the ones ask()
    # already made. RunConfig's 180s default timeout was observed timing out
    # against a free-tier OpenRouter model on a perfectly grounded answer —
    # raised here so a slow model doesn't get misread as a low-faithfulness one.
    result = evaluate(
        dataset, metrics=[faithfulness], llm=llm_wrapper, embeddings=emb_wrapper,
        run_config=RunConfig(timeout=300), raise_exceptions=False,
    )
    score = result["faithfulness"][0]
    if score is None or (isinstance(score, float) and math.isnan(score)):
        # NaN covers both "0 statements extracted" (a legitimately trivial answer)
        # and a swallowed internal error/timeout (raise_exceptions=False hides
        # which). Treating it as 0.0/"low" is the safe default for a legal QA
        # tool, but check server logs for a ragas "Exception raised in Job[...]"
        # line before trusting an all-"low" run as a real faithfulness signal.
        logger.warning(
            "score_faithfulness got NaN/None for question=%r — treating as 0.0. "
            "Check logs above for a ragas internal exception (e.g. a timeout) "
            "before assuming this reflects real low faithfulness.", question
        )
        return 0.0
    return float(score)


def confidence_bucket(score: float) -> Confidence:
    if score >= FAITHFULNESS_ABSTAIN_THRESHOLD:
        return "high"
    if score >= FAITHFULNESS_LOW_THRESHOLD:
        return "medium"
    return "low"


def apply_confidence(question: str, answer: str, contexts: list[str]) -> tuple[str, Confidence, float]:
    """Returns (answer to actually return, confidence bucket, raw faithfulness score).

    Below FAITHFULNESS_ABSTAIN_THRESHOLD the answer is replaced with an explicit
    abstention message rather than ever surfacing a low-faithfulness generation —
    but the confidence field still reports the real "medium"/"low" bucket rather
    than collapsing every abstention to the same label, so the score remains
    useful for reviewing false-abstains later.
    """
    if answer.strip() in _REFUSAL_MESSAGES:
        return answer, "low", 0.0

    score = score_faithfulness(question, answer, contexts)
    confidence = confidence_bucket(score)
    if confidence != "high":
        return ABSTENTION_MESSAGE, confidence, score
    return answer, confidence, score
