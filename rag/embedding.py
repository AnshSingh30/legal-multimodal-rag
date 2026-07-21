from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

PERSIST_DIR = "./chroma_db"
embedder = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def build_vectorstore(docs: list[Document]) -> Chroma:
    return Chroma.from_documents(docs, embedder,
                                  persist_directory=PERSIST_DIR)

def load_vectorstore() -> Chroma:
    return Chroma(persist_directory=PERSIST_DIR,
                  embedding_function=embedder)
