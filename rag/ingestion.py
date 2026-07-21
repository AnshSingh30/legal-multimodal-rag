import pathlib

import docx
import fitz
import pytesseract
from pdf2image import convert_from_path

from rag.tabular_ingest import extract_tabular_data


def _lines_from_grouped_words(grouped: dict[tuple, list[tuple]]) -> list[dict]:
    """Turn {line_key: [(x0, y0, x1, y1, word), ...]} into per-line text + union
    bounding box, so a chunk of text can later be matched back to the region(s)
    it came from."""
    lines = []
    for _key, items in sorted(grouped.items()):
        items.sort(key=lambda w: w[0])
        lines.append({
            "text": " ".join(w[4] for w in items),
            "bbox": [
                min(w[0] for w in items),
                min(w[1] for w in items),
                max(w[2] for w in items),
                max(w[3] for w in items),
            ],
        })
    return lines


def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    pages = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text")

        grouped: dict[tuple, list[tuple]] = {}
        for x0, y0, x1, y1, word, block_no, line_no, _word_no in page.get_text("words"):
            grouped.setdefault((block_no, line_no), []).append((x0, y0, x1, y1, word))
        lines = _lines_from_grouped_words(grouped)

        pages.append({"text": text, "page": page_num + 1,
                       "source": pdf_path, "method": "text", "lines": lines})
    return pages


def extract_text_with_ocr(pdf_path: str) -> list[dict]:
    images = convert_from_path(pdf_path, dpi=300)
    pages = []
    for page_num, image in enumerate(images):
        text = pytesseract.image_to_string(image, lang='eng')

        # Tesseract bboxes are pixel coordinates in the 300dpi render used for OCR,
        # not PDF point space — the frontend must overlay them on that same rendering.
        data = pytesseract.image_to_data(image, lang='eng', output_type=pytesseract.Output.DICT)
        grouped: dict[tuple, list[tuple]] = {}
        for i, word in enumerate(data["text"]):
            if not word.strip():
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            left, top = data["left"][i], data["top"][i]
            right, bottom = left + data["width"][i], top + data["height"][i]
            grouped.setdefault(key, []).append((left, top, right, bottom, word))
        lines = _lines_from_grouped_words(grouped)

        pages.append({"text": text, "page": page_num + 1,
                       "source": pdf_path, "method": "ocr", "lines": lines})
    return pages


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
