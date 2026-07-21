from rag.confidence import (
    ABSTENTION_MESSAGE,
    FAITHFULNESS_ABSTAIN_THRESHOLD,
    FAITHFULNESS_LOW_THRESHOLD,
    apply_confidence,
    confidence_bucket,
)
from rag.generation import NO_ANSWER_PHRASE, NO_CITATION_FALLBACK


def test_confidence_bucket_thresholds() -> None:
    assert confidence_bucket(FAITHFULNESS_ABSTAIN_THRESHOLD) == "high"
    assert confidence_bucket(1.0) == "high"
    assert confidence_bucket(FAITHFULNESS_ABSTAIN_THRESHOLD - 0.01) == "medium"
    assert confidence_bucket(FAITHFULNESS_LOW_THRESHOLD) == "medium"
    assert confidence_bucket(FAITHFULNESS_LOW_THRESHOLD - 0.01) == "low"
    assert confidence_bucket(0.0) == "low"


def test_apply_confidence_short_circuits_on_existing_refusal() -> None:
    # Refusal messages carry no claims to fact-check, so this must not attempt
    # a real RAGAS/LLM call — if it did, this test would hang or hit the network.
    answer, confidence, score = apply_confidence("q", NO_ANSWER_PHRASE, ["some context"])
    assert answer == NO_ANSWER_PHRASE
    assert confidence == "low"
    assert score == 0.0

    answer, confidence, score = apply_confidence("q", NO_CITATION_FALLBACK, ["some context"])
    assert answer == NO_CITATION_FALLBACK
    assert confidence == "low"
    assert score == 0.0


def test_abstention_message_differs_from_phase3_fallbacks() -> None:
    assert ABSTENTION_MESSAGE not in (NO_ANSWER_PHRASE, NO_CITATION_FALLBACK)
