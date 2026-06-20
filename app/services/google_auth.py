import logging
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.services.drive import SCOPES

logger = logging.getLogger(__name__)

TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "token.json")
CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")


def _load_credentials() -> Credentials | None:
    if os.path.exists(TOKEN_PATH):
        return Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    return None


def _save_credentials(creds: Credentials) -> None:
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())


def get_credentials() -> Credentials:
    """
    Return valid Google credentials, refreshing automatically if expired.
    Raises RuntimeError if credentials are missing and no browser is available.
    Opens the browser only on the very first run (or after token deletion).
    """
    creds = _load_credentials()

    if creds and creds.expired and creds.refresh_token:
        logger.info("Google token expired — refreshing automatically")
        creds.refresh(Request())
        _save_credentials(creds)
        return creds

    if creds and creds.valid:
        return creds

    if not os.path.exists(CREDENTIALS_PATH):
        raise RuntimeError(
            f"Google credentials file not found at '{CREDENTIALS_PATH}'. "
            "Download it from GCP Console → APIs & Services → Credentials."
        )

    logger.info("No valid token found — opening browser for one-time authorization")
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    _save_credentials(creds)
    logger.info("Authorization complete. Token saved to '%s'", TOKEN_PATH)
    return creds


def get_google_services():
    """Return authenticated (classroom, drive, youtube) service clients."""
    creds = get_credentials()
    classroom = build("classroom", "v1", credentials=creds)
    drive = build("drive", "v3", credentials=creds)
    youtube = build("youtube", "v3", credentials=creds)
    return classroom, drive, youtube
