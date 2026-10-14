# src/core/ingestion/vlm_extractor.py
from google import genai
from PIL import Image
import io
from src.core.config import settings

client = genai.Client(api_key=settings.google_api_key)


def extract_text_with_vlm(page) -> str:
    """
    Renders the page as an image and asks a vision-language model to
    transcribe it. More robust than character-level OCR for pages with
    broken font encoding, since the model uses linguistic context to
    resolve ambiguous glyphs, not just shape-matching.
    """
    if not settings.google_api_key or settings.google_api_key == "google_api_key":
        return ""

    try:
        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[
                "Transcribe all text from this academic paper page exactly as written. "
                "Preserve paragraph breaks. Do not summarize, explain, or add anything — "
                "output only the transcribed text.",
                img,
            ]
        )
        return response.text
    except Exception as e:
        print(f"VLM extraction failed: {e}")
        return ""
