from openai import AzureOpenAI

from config import settings


def _client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT.rstrip("/"),
    )


def get_embedding(text: str) -> list[float]:
    """Get embedding for text using Azure OpenAI embedding deployment."""
    if not text or not text.strip():
        # Return zero vector for empty (dim depends on model; 1536 for ada-002)
        return [0.0] * 1536
    client = _client()
    resp = client.embeddings.create(
        model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
        input=text.strip()[:8000],
    )
    return resp.data[0].embedding
