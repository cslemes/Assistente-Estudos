import os

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["auth"])


@router.post("/auth/google")
def authorize_google():
    """
    One-time Google OAuth setup. Opens a browser on the machine running the
    server, completes the flow, and saves token.json.  After this succeeds,
    /sync and /upload never open a browser again — the token is refreshed
    automatically for the lifetime of the refresh token (~6 months of inactivity).
    """
    if not os.path.exists(os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")):
        raise HTTPException(
            status_code=400,
            detail="credentials.json not found. Download it from GCP Console → APIs & Services → Credentials.",
        )

    try:
        from app.services.google_auth import get_credentials
        creds = get_credentials()
        return {
            "status": "authorized",
            "token_path": os.getenv("GOOGLE_TOKEN_PATH", "token.json"),
            "scopes": creds.scopes,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/google/status")
def google_auth_status():
    """Check whether a valid Google token exists without triggering auth."""
    from app.services.google_auth import TOKEN_PATH, _load_credentials
    creds = _load_credentials()
    if not creds:
        return {"status": "no_token", "token_path": TOKEN_PATH}
    if creds.valid:
        return {"status": "valid", "token_path": TOKEN_PATH}
    if creds.expired and creds.refresh_token:
        return {"status": "expired_refreshable", "token_path": TOKEN_PATH}
    return {"status": "invalid", "token_path": TOKEN_PATH}
