"""
AI Detection checker using ZeroGPT's public API.

Provides a simple interface to check how much of a text is detected as AI-generated.
Returns a structured result that can be displayed in the Streamlit UI.
"""

import requests
import time


ZEROGPT_API_URL = "https://api.zerogpt.com/api/detect/detectText"


def check_ai_score(text: str, api_key: str = "") -> dict:
    """
    Sends text to ZeroGPT API and returns an AI detection report.

    Args:
        text: The text to analyse (min 250 characters for reliable results).
        api_key: ZeroGPT API key. Falls back to browser-style public endpoint if not provided.

    Returns:
        dict with keys:
            - ai_percentage: float (0-100)
            - is_ai: bool
            - label: str ("Human", "Mixed", "AI", "Too Short", "Error")
            - word_count: int
            - feedback: str (human-readable summary)
            - error: str | None
    """
    if len(text.strip()) < 250:
        return {
            "ai_percentage": None,
            "is_ai": None,
            "label": "Too Short",
            "word_count": len(text.split()),
            "feedback": "Text is too short for reliable AI detection (minimum ~250 characters needed).",
            "error": None,
        }

    # Use browser-style headers — works with ZeroGPT's public endpoint
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": "https://www.zerogpt.com",
        "Referer": "https://www.zerogpt.com/",
    }
    # Add API key header if user has a paid account with credits
    if api_key and api_key not in ("ZEROGPT_API_KEY", ""):
        headers["ApiKey"] = api_key

    payload = {"input_text": text}

    try:
        resp = requests.post(
            ZEROGPT_API_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        if not data.get("success", False):
            msg = data.get("message", "Unknown error from ZeroGPT API")
            return _error_result(f"ZeroGPT API: {msg}")

        result_data = data.get("data", {})
        if result_data is None:
            return _error_result("ZeroGPT returned no data. Text may be too short or rate limited.")

        fake_pct = float(result_data.get("fakePercentage", 0))
        is_human = int(result_data.get("isHuman", 0))  # 100 = fully human, 0 = fully AI
        word_count = int(result_data.get("textWords", len(text.split())))

        if fake_pct <= 20:
            label = "Human"
        elif fake_pct <= 55:
            label = "Mixed"
        else:
            label = "AI"

        feedback = _build_feedback(fake_pct, label)

        return {
            "ai_percentage": round(fake_pct, 1),
            "is_ai": fake_pct > 50,
            "label": label,
            "word_count": word_count,
            "feedback": feedback,
            "error": None,
        }

    except requests.exceptions.HTTPError as e:
        return _error_result(f"ZeroGPT API HTTP error: {e.response.status_code} — {e.response.text[:200]}")
    except requests.exceptions.Timeout:
        return _error_result("ZeroGPT API timed out. Try again in a moment.")
    except requests.exceptions.ConnectionError:
        return _error_result("Could not connect to ZeroGPT. Check internet connection.")
    except Exception as e:
        return _error_result(f"Unexpected error: {e}")


def _build_feedback(pct: float, label: str) -> str:
    if label == "Human":
        return f"✅ {pct:.1f}% AI detected — looks human-written. Good to go."
    elif label == "Mixed":
        return f"⚠️ {pct:.1f}% AI detected — mixed content. Run humanizer again or edit manually."
    else:
        return f"🔴 {pct:.1f}% AI detected — clearly AI-generated. Needs humanization."


def _error_result(msg: str) -> dict:
    return {
        "ai_percentage": None,
        "is_ai": None,
        "label": "Error",
        "word_count": 0,
        "feedback": msg,
        "error": msg,
    }
