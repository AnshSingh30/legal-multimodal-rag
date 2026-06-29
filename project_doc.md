# Legal Multi-Modal RAG (Document & Tabular Q&A) — Project Documentation

## 1. Project Overview
The **Legal Multi-Modal RAG** is a production-grade Retrieval-Augmented Generation system. It allows users to upload complex legal PDF documents (both text-based and scanned) as well as tabular data (CSV, Excel, SQL), and ask natural language questions about them. The system guarantees that answers are grounded strictly in the provided documents with explicit citations (e.g., `[Source: filename.csv, Row X]`). Furthermore, it features an intelligent routing system that detects when a query requires a visual representation and automatically generates Plotly charts to augment the text response.

## 2. Architecture & Tech Stack

- **Frontend Interface:** Streamlit (`app.py`)
- **Backend Framework:** LangChain (using LCEL - LangChain Expression Language)
- **PDF Extraction:** PyMuPDF (`fitz`) and PyTesseract / `pdf2image` (for OCR fallback)
- **Tabular Data Extraction:** Pandas, OpenPyXL, SQLparse
- **Embeddings:** HuggingFace Local Embeddings (`all-MiniLM-L6-v2`) via `sentence-transformers`
- **Vector Database:** Chroma DB (Stored locally in `./chroma_db`)
- **Large Language Model (LLM):** OpenRouter API (Default: `google/gemini-1.5-flash`)
- **Chart Generation:** Plotly (`plotly.graph_objects`)
- **Evaluation:** RAGAS (for evaluating faithfulness, relevancy, and recall)

*(Note: The system was recently migrated to run entirely on a single OpenRouter API key, utilizing free local embeddings to completely eliminate the need for Google or Cohere API keys.)*

---

## 3. The Data Pipeline (Stage by Stage)

The pipeline is entirely contained within the `pipeline/` directory.

### Stage 1: Ingestion (`pipeline/ingest.py` & `pipeline/tabular_ingest.py`)
The `smart_extract` function handles multi-modal document ingestion.
1. **Tabular Data (.csv, .xlsx, .sql):** It delegates to `tabular_ingest.py`, which parses the tables using Pandas/SQLparse. It creates a global schema summary chunk and individual row-level data chunks.
2. **PDF Documents (.pdf):** It attempts to read the PDF using **PyMuPDF**. If it detects fewer than 100 characters across the entire document (indicating a scanned PDF), it automatically falls back to **OCR** using `pdf2image` and `pytesseract`.

### Stage 2: Chunking (`pipeline/chunker.py`)
Documents must be broken into smaller pieces for the AI to process effectively.
- **Tabular Data:** Tabular documents bypass text splitting entirely since row-level data is already at the optimal granularity.
- **PDF Data:** Uses LangChain's `RecursiveCharacterTextSplitter` (Chunk Size: 800 chars, Overlap: 150 chars).
- **Metadata:** Every chunk is tagged with its source filename, page/row index, and `data_type` so the LLM can accurately cite its sources later.

### Stage 3: Embedding & Storage (`pipeline/embedder.py`)
The text is converted into mathematical vectors (embeddings) and stored.
- Uses **HuggingFace Local Embeddings** (`all-MiniLM-L6-v2`). This model runs locally on your machine and incurs no API costs.
- Vectors are stored persistently in a local **Chroma DB** instance (`./chroma_db`). 

### Stage 4: Retrieval (`pipeline/retriever.py`)
When a user asks a question, the system queries Chroma using **Maximum Marginal Relevance (MMR)**. It fetches a larger pool of candidate documents (20) and narrows them down to the 5 best matches, optimizing for both strict relevance *and* diversity of information.

### Stage 5: Generation & Charting (`pipeline/generator.py`)
The top 5 chunks are sent to the OpenRouter LLM through a multi-step generation phase:
1. **Text Generation:** The chain uses LCEL to generate an answer grounded in the retrieved context, citing sources explicitly.
2. **Chart Detection (`chart_detector.py`):** A secondary lightweight LLM call evaluates the user's question to determine if a chart is requested (e.g., trends, comparisons, proportions).
3. **Chart Generation (`chart_generator.py`):** If a chart is needed, a third LLM call extracts structured JSON data from the text answer and dynamically constructs a `Plotly` graph (Bar, Line, Pie, Scatter, or Table).
4. **Output:** The final payload returned to the frontend contains both the text answer and the optional interactive Plotly figure.

### Stage 6: Evaluation (`pipeline/evaluator.py`)
An independent script designed to test the system's accuracy using the **RAGAS** framework to generate metrics for Faithfulness, Answer Relevancy, and Context Recall.

---

## 4. Environment Variables Required

The system requires only **one** API key stored in a `.env` file at the root of the project:
```env
OPENROUTER_API_KEY="your-openrouter-key"
```

## 5. Usage

To run the application, activate the virtual environment and start Streamlit:
```bash
source venv/bin/activate
streamlit run app.py
```
From the browser UI, users can upload PDFs, CSVs, Excel files, or SQL dumps. After clicking **Index Documents**, users can chat with the dataset. The system will seamlessly answer factual questions with citations, or render interactive Plotly charts above the text answer for analytical questions.
