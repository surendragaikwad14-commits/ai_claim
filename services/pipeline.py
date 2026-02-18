"""
Verification pipeline: extract → document-type check → LLM extraction → content embedding → similarity → diff → agent → save.
"""
from typing import Any, Optional

from config import settings
from . import (
    get_db,
    save_claim,
    list_claims,
    extract_text_from_pdf,
    find_most_similar_claim,
    compute_differences,
    get_verdict_and_reason,
    get_embedding,
)
from .agent import check_is_claim_document, extract_claim_fields_with_llm
from .diff_extractor import key_fields_indicate_different_claim, build_content_string_for_embedding
from .db import get_next_claim_id


def run_verification(file_bytes: bytes, filename: str = "") -> dict[str, Any]:
    """
    Run full pipeline on uploaded PDF. Returns result dict for UI and saves to MongoDB.
    Rejects non-claim documents (e.g. resume). Uses LLM extraction and content-based embedding.
    """
    # 1. Text extraction
    extracted_text = extract_text_from_pdf(file_bytes, filename)
    if not extracted_text or len(extracted_text.strip()) < 10:
        return {
            "success": False,
            "error": "Could not extract enough text from the document. Please upload a valid PDF with readable text.",
            "claim_id": None,
        }

    # 2. Document-type check: reject non-claims (resume, invoice, etc.)
    doc_check = check_is_claim_document(extracted_text)
    if not doc_check.get("is_claim", True):
        reason = doc_check.get("reason", "").strip() or "Document is not a claim form."
        return {
            "success": False,
            "error": f"This document does not appear to be a claim form. {reason} Please upload an insurance/claim document.",
            "claim_id": None,
        }

    # 3. Key fields: LLM only (any language); no regex
    new_fields = extract_claim_fields_with_llm(extracted_text)
    if new_fields is None:
        return {
            "success": False,
            "error": "Could not extract claim details from this document. Please ensure it is a clear claim form and try again.",
            "claim_id": None,
        }
    content_string = build_content_string_for_embedding(new_fields)
    new_embedding = get_embedding(content_string) if content_string else get_embedding(extracted_text[:8000])

    # 4. Load existing claims and find most similar (by content embedding)
    existing = list_claims(limit=50)
    similar_list = find_most_similar_claim(
        content_string or extracted_text[:8000],
        existing,
        text_field="extracted_text",
        top_k=1,
        new_embedding=new_embedding,
    )

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
        existing_fields = best_match.get("key_fields") or {}

    # 5. Differences (new_fields from LLM above)
    differences = compute_differences(new_fields, existing_fields) if existing_fields else []

    # 6. Same form template but different claim? (e.g. different policy holder, policy, amount)
    # Avoid false duplicate when two forms share layout but are different claims.
    if compared_with and key_fields_indicate_different_claim(new_fields, existing_fields):
        duplication_pct = 0.0
        status = "accepted"
        key_differences_str = "Different claim (different policy holder, policy number, amount, or date)."
        rejection_reason = ""
    # 7. Agent verdict (only when we have a comparison and not already ruled different)
    elif compared_with and duplication_pct >= settings.DUPLICATION_THRESHOLD_PCT:
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

    # 8. Persist
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
