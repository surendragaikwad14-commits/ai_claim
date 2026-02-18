from typing import Optional

import numpy as np

from .embeddings import get_embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors; returns 0-1 scale (0-100%)."""
    va, vb = np.array(a, dtype=float), np.array(b, dtype=float)
    norm_a, norm_b = np.linalg.norm(va), np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


def _sim_to_pct(sim: float) -> float:
    """Map cosine sim to 0-100 percentage (cosine can be -1 to 1; we treat as 0-1 for similarity)."""
    return max(0.0, min(100.0, (sim + 1) / 2 * 100))


def find_most_similar_claim(
    new_text: str,
    existing_claims: list[dict],
    text_field: str = "extracted_text",
    top_k: int = 1,
    new_embedding: Optional[list[float]] = None,
) -> list[tuple[dict, float]]:
    """
    Compare new claim to existing claims via embeddings.
    If new_embedding is provided, use it; otherwise embed new_text.
    Returns list of (claim_doc, duplication_pct) sorted by similarity descending.
    """
    if not existing_claims:
        return []
    if new_embedding is not None:
        new_emb = new_embedding
    elif new_text:
        new_emb = get_embedding(new_text)
    else:
        return []

    results: list[tuple[dict, float]] = []

    for claim in existing_claims:
        text = claim.get(text_field) or claim.get("extracted_text") or ""
        if not text:
            continue
        existing_emb = claim.get("embedding")
        if existing_emb is None:
            existing_emb = get_embedding(text)
        sim = cosine_similarity(new_emb, existing_emb)
        pct = _sim_to_pct(sim)
        results.append((claim, round(pct, 1)))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]
