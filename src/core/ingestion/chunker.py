from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.core.config import settings


def chunk_pages(pages: list[dict]) -> list[dict]:

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    chunks = []
    for page in pages:
        split_texts = splitter.split_text(page["text"])
        for split_text in split_texts:
            chunks.append({
                "text": split_text,
                "source": page["source"],
                "page": page["page"],
            })

    return chunks
