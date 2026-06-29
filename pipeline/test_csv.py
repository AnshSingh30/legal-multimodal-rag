import os
from dotenv import load_dotenv
import pathlib
import sys

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.ingest import smart_extract
from pipeline.chunker import chunk_pages
from pipeline.embedder import build_vectorstore
from pipeline.retriever import build_retriever
from pipeline.generator import ask

def test_csv():
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
