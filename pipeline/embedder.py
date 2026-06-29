from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

PERSIST_DIR = "./chroma_db"
embedder = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def build_vectorstore(docs) -> Chroma:
    return Chroma.from_documents(docs, embedder,
                                  persist_directory=PERSIST_DIR)

def load_vectorstore() -> Chroma:
    return Chroma(persist_directory=PERSIST_DIR,
                  embedding_function=embedder)
