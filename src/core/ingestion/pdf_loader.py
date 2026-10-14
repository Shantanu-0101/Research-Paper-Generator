import pymupdf as fitz
from src.core.ingestion.vlm_extractor import extract_text_with_vlm

def _looks_corrupted(text: str, threshold: float = 0.01) -> bool:
    """
    Flags a page as likely having broken font encoding if '?' shows up
    far more often than real question marks would in normal prose.
    """
    if not text:
        return False
    return text.count("?") / len(text) > threshold



def extract_text_from_pdf(file_bytes: bytes, filename: str) -> list[dict]:

    pages = []
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception:
        return pages

    for page_num in range(len(doc)):
        text = doc[page_num].get_text("text").strip()

        if _looks_corrupted(text):
            print("VLM triggered")
            text = extract_text_with_vlm(doc[page_num]).strip()


        if text:
            pages.append({
                "text": text,
                "source": filename,
                "page": page_num + 1,
            })

    doc.close()
    return pages


def extract_text_from_uploads(uploaded_files) -> tuple[list[dict], list[str]]:

    all_pages = []
    skipped = []

    for uploaded_file in uploaded_files:
        file_bytes = uploaded_file.getvalue()
        pages = extract_text_from_pdf(file_bytes, uploaded_file.name)

        if pages:
            all_pages.extend(pages)
        else:
            skipped.append(uploaded_file.name)

    return all_pages, skipped
