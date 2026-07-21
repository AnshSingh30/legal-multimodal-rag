import os
from dotenv import load_dotenv
import pathlib
import sys

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.ingestion import smart_extract
from rag.chunking import chunk_pages
from rag.embedding import build_vectorstore
from rag.retrieval import build_retriever
from rag.generation import ask

def test_csv() -> None:
    print("--- TESTING CSV ---")
    pages = smart_extract("test_sample.csv")
    docs = chunk_pages(pages)
    vectorstore = build_vectorstore(docs)
    retriever = build_retriever(vectorstore)
    
    question = "Compare the scores of Alice, Bob and Charlie"
    print(f"Q: {question}")
    result = ask(question, retriever)
    print(f"A: {result['answer']}")
    print(f"Chart Needed: {result.get('chart') is not None}")
    if result.get("chart"):
        print(f"Chart Type: {result.get('chart_type')}")
        print(f"Chart Reason: {result.get('chart_reason')}")
    else:
        print("NO CHART GENERATED")

test_csv()
