import streamlit as st
from dotenv import load_dotenv   # FIX 3
import os, pathlib

load_dotenv()   # FIX 3 — must run before any pipeline import reads env vars

from pipeline.ingest import smart_extract
from pipeline.chunker import chunk_pages
from pipeline.embedder import build_vectorstore, load_vectorstore
from pipeline.retriever import build_retriever
from pipeline.generator import ask

UPLOAD_DIR = pathlib.Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

st.title("Legal Document Q&A")
st.caption("Upload PDFs, index them, then ask questions with cited answers.")

uploaded = st.file_uploader(
    "Upload documents",
    type=["pdf", "csv", "xlsx", "xls", "sql", "docx"],
    accept_multiple_files=True
)

if uploaded and st.button("Index documents"):
    with st.spinner("Extracting and indexing..."):
        all_docs = []
        for f in uploaded:
            save_path = UPLOAD_DIR / f.name
            save_path.write_bytes(f.read())
            pages = smart_extract(str(save_path))
            all_docs.extend(chunk_pages(pages))

        vectorstore = build_vectorstore(all_docs)
        st.session_state.retriever = build_retriever(vectorstore)
        
        # Display file badges
        for f in uploaded:
            ext = pathlib.Path(f.name).suffix.lower()
            badge = "PDF" if ext == ".pdf" else "CSV" if ext == ".csv" else "Excel" if ext in [".xlsx", ".xls"] else "SQL" if ext == ".sql" else "Word"
            st.success(f"[{badge}] Indexed {f.name}")

        st.success(f"Total: Indexed {len(all_docs)} chunks from {len(uploaded)} file(s).")

if "retriever" in st.session_state:
    question = st.text_input("Ask a question about your documents")
    if question:
        with st.spinner("Searching and generating answer..."):
            result = ask(question, st.session_state.retriever)

        if result.get("chart") is not None:
            st.plotly_chart(result["chart"], use_container_width=True)
            st.caption(f"📊 Auto-generated chart — {result.get('chart_reason')}")

        st.markdown(result["answer"])

        with st.expander("Sources used"):
            for doc in result["source_documents"]:
                src  = doc.metadata.get("source", "unknown")
                page = doc.metadata.get("page", "?")
                st.caption(f"{src} — Page {page}")
                st.text(doc.page_content[:300] + "...")
