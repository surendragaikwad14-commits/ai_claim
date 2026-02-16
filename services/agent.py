import json
from typing import Any

from openai import AzureOpenAI

from config import settings


def _client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT.rstrip("/"),
    )


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
