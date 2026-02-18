import json
import logging
from typing import Any

from openai import AzureOpenAI

from config import settings

logger = logging.getLogger(__name__)


def _client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT.rstrip("/"),
    )


def _parse_json_response(content: str) -> dict:
    """Strip markdown code block if present and parse JSON."""
    content = (content or "").strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(content) if content else {}


def check_is_claim_document(text: str) -> dict[str, Any]:
    """
    Classify whether the document is a claim (insurance/health/motor/any claim form).
    Reject resumes, invoices, general letters, etc.
    Returns {"is_claim": bool, "reason": str}.
    """
    if not text or len(text.strip()) < 20:
        return {"is_claim": False, "reason": "Document text too short to classify."}
    # Truncate for the classification call
    snippet = text.strip()[:6000]
    system = """You are a document classifier. Determine if this document is an INSURANCE/CLAIM document (e.g. claim form, health claim, motor claim, policy claim, reimbursement claim). It must be a claim-related form or request, not a resume/CV, invoice, contract, or other document type. Reply with valid JSON only, no markdown: {"is_claim": true or false, "reason": "one short sentence"}"""
    user = f"Document text:\n{snippet}\n\nIs this a claim document? Output JSON with is_claim and reason."
    try:
        client = _client()
        resp = client.chat.completions.create(
            model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
        )
        content = (resp.choices[0].message.content or "").strip()
        out = _parse_json_response(content)
        return {
            "is_claim": bool(out.get("is_claim", False)),
            "reason": str(out.get("reason", "")).strip() or "Classification completed.",
        }
    except Exception as e:
        logger.warning("Claim document check failed: %s", e)
        return {"is_claim": True, "reason": "Could not classify; allowing as claim."}


def extract_claim_fields_with_llm(text: str) -> dict[str, Any] | None:
    """
    Extract key claim fields from document text using LLM. Works in any language.
    Returns dict with keys claimant_name, policy_number, claim_amount, incident_date (values or None).
    Returns None on failure so caller can fall back to regex.
    """
    if not text or len(text.strip()) < 10:
        return None
    snippet = text.strip()[:8000]
    system = """You are a claim data extractor. From the given document text (which may be in any language: English, Hindi, Tamil, etc.), extract these key fields. Preserve original values as they appear. Use null for missing. Output valid JSON only, no markdown. Use exactly these keys: claimant_name, policy_number, claim_amount, incident_date. Example: {"claimant_name": "Rohan Sharma", "policy_number": "HL-99871234", "claim_amount": "82,450", "incident_date": "05/02/2026"}"""
    user = f"Document text:\n{snippet}\n\nExtract the four fields. Output JSON only."
    try:
        client = _client()
        resp = client.chat.completions.create(
            model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
        )
        content = (resp.choices[0].message.content or "").strip()
        out = _parse_json_response(content)
        # Normalize to our schema (string or None)
        result = {
            "claimant_name": out.get("claimant_name"),
            "policy_number": out.get("policy_number"),
            "claim_amount": out.get("claim_amount"),
            "incident_date": out.get("incident_date"),
        }
        result = {k: (str(v).strip() if v is not None else None) for k, v in result.items()}
        return result
    except Exception as e:
        logger.warning("LLM claim extraction failed: %s", e)
        return None


def get_verdict_and_reason(
    duplication_pct: float,
    compared_claim_id: str,
    differences: list[dict[str, str]],
    threshold_pct: float | None = None,
) -> dict[str, str]:
    """
    Agent decides: status (accepted / rejected / flagged), key_differences summary,
    and rejection_reason (why rejected, for dashboard).
    """
    threshold = threshold_pct if threshold_pct is not None else settings.DUPLICATION_THRESHOLD_PCT
    diffs_str = json.dumps(differences, indent=2) if differences else "No structured differences."

    system = """You are a claim verification assistant. Given duplication percentage and list of field differences between a new claim and an existing one, you must:
1. Decide status: "accepted" (clearly new claim), "rejected" (duplicate or suspicious), or "flagged" (needs human review).
2. Write a short "key_differences" line (one or two sentences) for Excel: e.g. "Claim amount changed from ₹1.2L to ₹1.5L; Incident date updated."
3. Write "rejection_reason" only when status is rejected or flagged: explain in one sentence why (e.g. "Duplicate of existing claim with material change in amount."). If status is accepted, set rejection_reason to empty string.

Respond with valid JSON only, no markdown:
{"status": "accepted|rejected|flagged", "key_differences": "...", "rejection_reason": "..."}"""

    user = f"""Duplication with existing claim: {duplication_pct}%.
Compared claim ID: {compared_claim_id}.
Structured differences:
{diffs_str}

Threshold for potential duplicate: {threshold}%.
Output JSON with status, key_differences, and rejection_reason."""

    client = _client()
    resp = client.chat.completions.create(
        model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    content = (resp.choices[0].message.content or "").strip()
    # Strip markdown code block if present
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        out = json.loads(content)
    except json.JSONDecodeError:
        out = {
            "status": "flagged",
            "key_differences": "Unable to parse differences.",
            "rejection_reason": "Agent could not classify; manual review required.",
        }
    return {
        "status": out.get("status", "flagged"),
        "key_differences": out.get("key_differences", ""),
        "rejection_reason": out.get("rejection_reason", ""),
    }
