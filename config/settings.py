import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


class Settings:
    # MongoDB
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "claim_db")
    MONGODB_CLAIMS_COLLECTION: str = os.getenv("MONGODB_CLAIMS_COLLECTION", "claims")

    # Azure OpenAI
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    AZURE_OPENAI_CHAT_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = os.getenv(
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002"
    )

    # Similarity threshold (treat as potential duplicate above this %)
    DUPLICATION_THRESHOLD_PCT: float = float(os.getenv("DUPLICATION_THRESHOLD_PCT", "70"))

    # OCR: use Azure vision (gpt-4o-mini) for image PDFs when True; else Tesseract
    USE_AZURE_OCR: bool = os.getenv("USE_AZURE_OCR", "false").lower() in ("true", "1", "yes")

    # OCR language(s) for image-only PDFs (e.g. "eng", "hin+eng" for Hindi+English)
    TESSERACT_LANG: str = os.getenv("TESSERACT_LANG", "eng")


settings = Settings()
