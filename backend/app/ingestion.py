import re
from io import BytesIO

from pypdf import PdfReader


CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


def extract_chunks(pdf_bytes: bytes) -> list[dict[str, int | str]]:
    reader = PdfReader(BytesIO(pdf_bytes))
    chunks: list[dict[str, int | str]] = []
    step = CHUNK_SIZE - CHUNK_OVERLAP

    for page_number, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        text = re.sub(r"\s+", " ", raw_text).strip()

        for start in range(0, len(text), step):
            chunk_text = text[start : start + CHUNK_SIZE].strip()
            if not chunk_text:
                continue
            chunks.append(
                {
                    "chunk_id": len(chunks),
                    "page": page_number,
                    "text": chunk_text,
                }
            )

    return chunks
