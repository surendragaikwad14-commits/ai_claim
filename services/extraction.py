import base64
import io
import logging
from typing import Optional

import pdfplumber

from config import settings

logger = logging.getLogger(__name__)

# Minimum characters from embedded text to skip OCR fallback
_MIN_EMBEDDED_TEXT_LEN = 10

# Prompt for Azure vision OCR (same deployment as chat; gpt-4o-mini supports vision)
_AZURE_OCR_PROMPT = """Extract all text from this document image. Preserve order, layout, and line breaks. Output plain text only, no markdown or commentary. If the document is in multiple languages (e.g. English and Hindi), include all text as it appears."""


def _extract_with_azure_vision(file_bytes: bytes) -> str:
    """Extract text from PDF using Azure OpenAI vision (gpt-4o-mini) on each page image."""
    try:
        from pdf2image import convert_from_bytes
        from openai import AzureOpenAI
    except ImportError as e:
        logger.warning("Azure vision OCR unavailable (missing pdf2image or openai): %s", e)
        return ""
    if not settings.AZURE_OPENAI_API_KEY or not settings.AZURE_OPENAI_ENDPOINT:
        logger.warning("Azure OpenAI not configured; skipping Azure vision OCR.")
        return ""
    try:
        images = convert_from_bytes(file_bytes, dpi=200)
    except Exception as e:
        logger.warning("Could not convert PDF to images (install poppler): %s", e)
        return ""
    client = AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT.rstrip("/"),
    )
    text_parts = []
    for i, img in enumerate(images):
        try:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
            url = f"data:image/png;base64,{b64}"
            resp = client.chat.completions.create(
                model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _AZURE_OCR_PROMPT},
                            {"type": "image_url", "image_url": {"url": url}},
                        ],
                    }
                ],
                temperature=0.0,
                max_tokens=4096,
            )
            content = (resp.choices[0].message.content or "").strip()
            if content:
                text_parts.append(content)
        except Exception as e:
            logger.warning("Azure vision OCR failed for page %s: %s", i + 1, e)
    return "\n\n".join(p.strip() for p in text_parts if p and p.strip())


def _extract_with_ocr(file_bytes: bytes) -> str:
    """Extract text from PDF using Tesseract OCR (for image-only / screenshot PDFs).
    Uses TESSERACT_LANG from config (e.g. 'eng', 'hin+eng' for Hindi+English)."""
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        from config import settings
    except ImportError as e:
        logger.warning("OCR fallback unavailable (missing pdf2image or pytesseract): %s", e)
        return ""
    try:
        images = convert_from_bytes(file_bytes, dpi=200)
    except Exception as e:
        logger.warning("Could not convert PDF to images (install poppler): %s", e)
        return ""
    lang = getattr(settings, "TESSERACT_LANG", "eng") or "eng"
    text_parts = []
    for img in images:
        try:
            text_parts.append(pytesseract.image_to_string(img, lang=lang))
        except Exception as e:
            logger.warning("Tesseract OCR failed (lang=%s, install tesseract and language pack): %s", lang, e)
            return ""
    return "\n\n".join(p.strip() for p in text_parts if p and p.strip())


def extract_text_from_pdf(file_bytes: bytes, filename: str = "") -> str:
    """Extract plain text from PDF: embedded text via pdfplumber, then OCR fallback for image-only PDFs."""
    text_parts = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
    except Exception as e:
        return f"[Extraction error: {e}]"
    result = "\n\n".join(text_parts) if text_parts else ""
    if result.strip() and len(result.strip()) >= _MIN_EMBEDDED_TEXT_LEN:
        return result
    # OCR path: Azure vision first if enabled, else Tesseract; fallback to Tesseract on Azure failure
    ocr_text = ""
    if settings.USE_AZURE_OCR:
        ocr_text = _extract_with_azure_vision(file_bytes)
    if not ocr_text or len(ocr_text.strip()) < _MIN_EMBEDDED_TEXT_LEN:
        ocr_text = _extract_with_ocr(file_bytes)
    if ocr_text and len(ocr_text.strip()) >= _MIN_EMBEDDED_TEXT_LEN:
        return ocr_text
    return result if result else ocr_text
