from fastapi import Header, HTTPException
from app.config.settings import Settings


def require_api_key(x_api_key: str = Header(default="")) -> None:
    """Verify X-Api-Key header against BACKEND_API_KEY setting.

    No-op when BACKEND_API_KEY is empty (local dev without the env var set).
    """
    key = Settings().backend_api_key
    if key and x_api_key != key:
        raise HTTPException(status_code=401, detail="Unauthorized")
