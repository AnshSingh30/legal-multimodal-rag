from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_recall
from datasets import Dataset   # FIX: must use HuggingFace Dataset object

def evaluate_pipeline(pipeline_ask_fn, retriever, qa_pairs: list[dict], llm, embeddings) -> dict:
    """
    qa_pairs: [{"question": str, "ground_truth": str}, ...]
    pipeline_ask_fn: callable matching ask(question, retriever) -> dict
    """
    questions, answers, contexts, ground_truths = [], [], [], []

    import time
    for pair in qa_pairs:
        print(f"Asking: {pair['question']}")
        result = pipeline_ask_fn(pair["question"], retriever)
        time.sleep(5) # Throttle to prevent 429 RateLimitError on OpenRouter free keys
        questions.append(pair["question"])
        answers.append(result["answer"])
        contexts.append([d.page_content for d in result["source_documents"]])
        ground_truths.append(pair["ground_truth"])

    # FIX 4: RAGAS ≥0.1 requires datasets.Dataset, not a plain dict
    dataset = Dataset.from_dict({
        "question":    questions,
        "answer":      answers,
        "contexts":    contexts,
        "ground_truth": ground_truths
    })

    scores = evaluate(dataset, metrics=[
        faithfulness
    ], llm=llm, embeddings=embeddings, raise_exceptions=False)
    return scores
import os
import json
import sys
import types

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Monkey-patch to fix Ragas v0.1 import bug with newer langchain_community
sys.modules['langchain_community.chat_models.vertexai'] = types.ModuleType('langchain_community.chat_models.vertexai')
sys.modules['langchain_community.chat_models.vertexai'].ChatVertexAI = type('ChatVertexAI', (object,), {})

from dotenv import load_dotenv

load_dotenv()

from pipeline.ingest import smart_extract
from pipeline.chunker import chunk_pages
from pipeline.embedder import build_vectorstore, embedder
from pipeline.retriever import build_retriever
from pipeline.generator import ask, _get_llm

def run():
    print("Extracting and chunking...")
    pages = smart_extract("test_sample.csv")
    docs = chunk_pages(pages)
    
    print("Building vectorstore...")
    vectorstore = build_vectorstore(docs)
    retriever = build_retriever(vectorstore)
    
    qa_pairs = [
        {"question": "What is the score of Alice?", "ground_truth": "Alice's score is 90."}
    ]
    
    print("Evaluating...")
    llm = _get_llm()
    try:
        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper
        llm_wrapper = LangchainLLMWrapper(llm)
        emb_wrapper = LangchainEmbeddingsWrapper(embedder)
        scores = evaluate_pipeline(ask, retriever, qa_pairs, llm_wrapper, emb_wrapper)
    except ImportError:
        # Fallback for older ragas versions
        scores = evaluate_pipeline(ask, retriever, qa_pairs, llm, embedder)
    
    print("----- EVALUATION RESULTS -----")
    print(scores)

if __name__ == "__main__":
    run()
