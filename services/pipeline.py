"""
Single verification pipeline: extract → similarity → diff → agent → save.
"""
from typing import Any, Optional

from config import settings
from . import (
    get_db,
    save_claim,
    list_claims,
    extract_text_from_pdf,
    find_most_similar_claim,
    extract_key_fields,
    compute_differences,
    get_verdict_and_reason,
    get_embedding,
)
from .db import get_next_claim_id


def run_verification(file_bytes: bytes, filename: str = "") -> dict[str, Any]:
    """
    Run full pipeline on uploaded PDF. Returns result dict for UI and saves to MongoDB.
    """
    # 1. Text extraction
    extracted_text = extract_text_from_pdf(file_bytes, filename)
    if not extracted_text or len(extracted_text.strip()) < 10:
        return {
            "success": False,
            "error": "Could not extract enough text from the document. Please upload a valid PDF with readable text.",
            "claim_id": None,
        }

    # 2. Load existing claims (with text/embedding for similarity)
    existing = list_claims(limit=50)
    # Exclude embedding from response when sending to UI later; keep in memory for similarity
    new_embedding = get_embedding(extracted_text)
    similar_list = find_most_similar_claim(extracted_text, existing, text_field="extracted_text", top_k=1)

    compared_with: Optional[str] = None
    duplication_pct: float = 0.0
    key_differences_str = ""
    rejection_reason = ""
    status = "accepted"
    existing_fields = {}

    if similar_list:
        best_match, pct = similar_list[0]
        compared_with = best_match.get("claim_id") or str(best_match.get("_id", ""))
        duplication_pct = pct
        existing_fields = best_match.get("key_fields") or extract_key_fields(best_match.get("extracted_text") or "")

    # 3. Key fields and differences
    new_fields = extract_key_fields(extracted_text)
    differences = compute_differences(new_fields, existing_fields) if existing_fields else []

    # 4. Agent verdict (only when we have a comparison)
    if compared_with and duplication_pct >= settings.DUPLICATION_THRESHOLD_PCT:
        agent_out = get_verdict_and_reason(duplication_pct, compared_with, differences)
        status = agent_out["status"]
        key_differences_str = agent_out["key_differences"]
        rejection_reason = agent_out["rejection_reason"]
    elif compared_with:
        key_differences_str = "; ".join(
            f"{d['field']}: {d['old_value']} → {d['new_value']}" for d in differences
        ) or "No significant differences."
        if duplication_pct >= 50:
            status = "flagged"
            rejection_reason = f"Moderate similarity ({duplication_pct}%) with {compared_with}; review recommended."

    # 5. Persist
    claim_id = get_next_claim_id()
    doc = {
        "claim_id": claim_id,
        "filename": filename,
        "extracted_text": extracted_text,
        "embedding": new_embedding,
        "key_fields": new_fields,
        "status": status,
        "compared_with": compared_with,
        "duplication_pct": duplication_pct,
        "key_differences": key_differences_str,
        "rejection_reason": rejection_reason,
        "created_at": None,  # set by MongoDB or we set below
    }
    from datetime import datetime, timezone
    doc["created_at"] = datetime.now(timezone.utc)
    save_claim(doc)

    return {
        "success": True,
        "claim_id": claim_id,
        "compared_with": compared_with,
        "duplication_pct": duplication_pct,
        "key_differences": key_differences_str,
        "status": status,
        "rejection_reason": rejection_reason,
        "error": None,
    }
