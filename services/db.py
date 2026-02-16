from typing import Any, Optional

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

from config import settings

_db: Optional[Database] = None


def get_db() -> Database:
    global _db
    if _db is None:
        if not settings.MONGODB_URI:
            raise ValueError("MONGODB_URI is not set in .env")
        client = MongoClient(settings.MONGODB_URI)
        _db = client[settings.MONGODB_DB_NAME]
    return _db


def _claims_collection() -> Collection:
    return get_db()[settings.MONGODB_CLAIMS_COLLECTION]


def save_claim(doc: dict[str, Any]) -> str:
    coll = _claims_collection()
    result = coll.insert_one(doc)
    return str(result.inserted_id)


def list_claims(
    status: Optional[str] = None,
    limit: int = 100,
    exclude_large_fields: bool = False,
) -> list[dict]:
    coll = _claims_collection()
    q = {} if status is None else {"status": status}
    proj = None
    if exclude_large_fields:
        proj = {"extracted_text": 0, "embedding": 0}
    cursor = coll.find(q, proj).sort("created_at", -1).limit(limit)
    return list(cursor)


def get_claim_by_id(claim_id: str) -> Optional[dict]:
    coll = _claims_collection()
    return coll.find_one({"claim_id": claim_id})


def get_next_claim_id() -> str:
    """Generate next claim ID: Claim_YYYY_NNN (e.g. Claim_2026_101)."""
    from datetime import datetime, timezone
    coll = _claims_collection()
    year = datetime.now(timezone.utc).strftime("%Y")
    prefix = f"Claim_{year}_"
    # Count docs with this prefix
    n = coll.count_documents({"claim_id": {"$regex": f"^{prefix}"}})
    return f"{prefix}{n + 1:03d}"
