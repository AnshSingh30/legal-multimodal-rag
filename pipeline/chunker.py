from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from datetime import date

def chunk_pages(pages: list[dict]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    docs = []
    for page in pages:
        if page.get("metadata", {}).get("data_type") == "tabular":
            docs.append(Document(
                page_content=page["text"],
                metadata={
                    **page["metadata"],
                    "date_ingested": str(date.today())
                }
            ))
        else:
            chunks = splitter.split_text(page["text"])
            for i, chunk in enumerate(chunks):
                docs.append(Document(
                    page_content=chunk,
                    metadata={
                        "source": page["source"],
                        "page": page["page"],
                        "chunk_index": i,
                        "method": page.get("method", "text"),
                        "date_ingested": str(date.today())
                    }
                ))
    return docs
