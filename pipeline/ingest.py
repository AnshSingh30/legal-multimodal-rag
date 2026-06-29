import fitz
import pytesseract
from pdf2image import convert_from_path

def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    pages = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        pages.append({"text": text, "page": page_num + 1,
                       "source": pdf_path, "method": "text"})
    return pages

def extract_text_with_ocr(pdf_path: str) -> list[dict]:
    images = convert_from_path(pdf_path, dpi=300)
    pages = []
    for page_num, image in enumerate(images):
        text = pytesseract.image_to_string(image, lang='eng')
        pages.append({"text": text, "page": page_num + 1,
                       "source": pdf_path, "method": "ocr"})
    return pages

from pipeline.tabular_ingest import extract_tabular_data
import pathlib
import docx

def extract_text_from_docx(docx_path: str) -> list[dict]:
    doc = docx.Document(docx_path)
    # Combine paragraphs into a single text block since Word docs don't always have hard page breaks
    text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    # Optionally, we could try to chunk by page breaks or headings, but treating as a single page is simplest
    # Chunking later will split it up appropriately
    return [{"text": text, "page": 1, "source": docx_path, "method": "docx"}]

def smart_extract(file_path: str) -> list[dict]:
    ext = pathlib.Path(file_path).suffix.lower()
    
    if ext == ".docx":
        return extract_text_from_docx(file_path)
        
    if ext in [".csv", ".xlsx", ".xls", ".sql"]:
        return extract_tabular_data(file_path)
    
    pages = extract_text_from_pdf(file_path)
    if sum(len(p["text"]) for p in pages) < 100:
        return extract_text_with_ocr(file_path)
    return pages
