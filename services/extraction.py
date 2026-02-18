import io
import logging
from typing import Optional

import pdfplumber

logger = logging.getLogger(__name__)

# Minimum characters from embedded text to skip OCR fallback
_MIN_EMBEDDED_TEXT_LEN = 10


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
    ocr_text = _extract_with_ocr(file_bytes)
    if ocr_text and len(ocr_text.strip()) >= _MIN_EMBEDDED_TEXT_LEN:
        return ocr_text
    return result if result else ocr_text
