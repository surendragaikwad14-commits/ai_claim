from typing import Any


def extract_key_fields(text: str) -> dict[str, Any]:
    """
    Simple heuristic extraction of key fields from claim text.
    Used as fallback; agent can override with structured extraction.
    """
    import re
    fields = {
        "claim_amount": None,
        "claimant_name": None,
        "incident_date": None,
        "policy_number": None,
    }
    # Amount: ₹1.2L, Rs 50000, INR 10000, 1,50,000 etc.
    amount_patterns = [
        r"[Rr]s\.?\s*([\d,]+(?:\.\d+)?)\s*(?:L|Lakh)?",
        r"₹\s*([\d,]+(?:\.\d+)?)\s*(?:L|Lakh)?",
        r"([\d,]+(?:\.\d+)?)\s*(?:L|Lakh|INR)",
        r"claim\s*amount[:\s]+([\d,]+(?:\.\d+)?)",
        r"amount[:\s]+([\d,]+(?:\.\d+)?)",
    ]
    for p in amount_patterns:
        m = re.search(p, text, re.I)
        if m:
            fields["claim_amount"] = m.group(1).strip()
            break

    # Policy number: alphanumeric, often with prefix
    policy_m = re.search(r"policy\s*(?:no|number|#)?[:\s]*([A-Za-z0-9\-/]+)", text, re.I)
    if policy_m:
        fields["policy_number"] = policy_m.group(1).strip()

    # Date: DD/MM/YYYY or DD-MM-YYYY or similar
    date_m = re.search(
        r"(?:incident|date|loss|accident)\s*(?:date)?[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        text,
        re.I,
    )
    if date_m:
        fields["incident_date"] = date_m.group(1).strip()
    else:
        date_m = re.search(r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
        if date_m:
            fields["incident_date"] = date_m.group(1).strip()

    # Claimant name: after "name" or "claimant"
    name_m = re.search(
        r"(?:claimant|name|insured)[:\s]*([A-Za-z\s]{2,50})",
        text,
        re.I,
    )
    if name_m:
        fields["claimant_name"] = name_m.group(1).strip()[:80]

    return fields


def compute_differences(
    new_fields: dict[str, Any],
    existing_fields: dict[str, Any],
) -> list[dict[str, str]]:
    """Compare two field dicts and return list of {field, old_value, new_value}."""
    diffs = []
    all_keys = set(new_fields) | set(existing_fields)
    for key in all_keys:
        ov = existing_fields.get(key)
        nv = new_fields.get(key)
        if ov is None and nv is None:
            continue
        if ov != nv:
            diffs.append({
                "field": key,
                "old_value": str(ov) if ov is not None else "—",
                "new_value": str(nv) if nv is not None else "—",
            })
    return diffs
