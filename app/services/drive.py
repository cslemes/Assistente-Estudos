import io
import json
import os
import re

from googleapiclient.http import MediaIoBaseDownload

MANIFEST_PATH = "downloaded_ids.json"


def _load_manifest() -> dict:
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    return {}


def _save_manifest(manifest: dict):
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
    "https://www.googleapis.com/auth/classroom.announcements.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/classroom.topics.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
]


def clean_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name)


def get_drive_links_from_form(url: str) -> list[str]:
    from playwright.sync_api import sync_playwright

    ids = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle")
        content = page.content()
        browser.close()

    patterns = [
        r"folders/([a-zA-Z0-9_-]{25,})",
        r"file/d/([a-zA-Z0-9_-]{25,})",
        r"id=([a-zA-Z0-9_-]{25,})",
    ]
    for pattern in patterns:
        ids.extend(re.findall(pattern, content))

    return list(dict.fromkeys(ids))


def get_organized_path(topic_path: str, filename: str) -> str:
    ext = filename.lower()

    if ext.endswith((".mp4", ".mkv", ".avi", ".mov")):
        subfolder = "video"
    elif ext.endswith((".ipynb", ".py", ".js", ".ts")):
        subfolder = "scripts"
    else:
        subfolder = "documentos"

    target_dir = os.path.join(topic_path, subfolder)
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(os.path.join(topic_path, "ai_data"), exist_ok=True)

    return os.path.join(target_dir, filename)


from app.config.settings import VIDEO_EXTENSIONS


def _find_any_video(directory: str) -> str | None:
    if not os.path.isdir(directory):
        return None
    for f in sorted(os.listdir(directory)):
        if f.lower().endswith(VIDEO_EXTENSIONS):
            return os.path.join(directory, f)
    return None


def download_file_direct(drive_service, file_id: str, full_path: str, title_prefix: str = "") -> str | None:
    manifest = _load_manifest()

    if file_id in manifest:
        print(f"[Skip] Já baixado (id={file_id}): {os.path.basename(manifest[file_id])}")
        return manifest[file_id]

    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    if os.path.exists(full_path):
        manifest[file_id] = full_path
        _save_manifest(manifest)
        print(f"[Skip] Já baixado: {os.path.basename(full_path)}")
        return full_path

    # File was renamed — check if any video already exists in the same subfolder
    if full_path.lower().endswith(VIDEO_EXTENSIONS):
        existing = _find_any_video(os.path.dirname(full_path))
        if existing:
            manifest[file_id] = existing
            _save_manifest(manifest)
            print(f"[Skip] Renomeado: {os.path.basename(existing)}")
            return existing

    try:
        request = drive_service.files().get_media(fileId=file_id)
        with io.FileIO(full_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request, chunksize=1024 * 1024 * 10)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        manifest[file_id] = full_path
        _save_manifest(manifest)
        print(f"[Success] {os.path.basename(full_path)}")
        return full_path
    except Exception as e:
        print(f"[Error] Falha no download de {file_id}: {e}")
        return None


def download_folder_recursive(drive_service, folder_id: str, local_path: str, title_prefix: str = "") -> list[str]:
    downloaded_paths = []
    try:
        results = (
            drive_service.files()
            .list(q=f"'{folder_id}' in parents and trashed = false",
                fields="files(id, name, mimeType)")
            .execute()
        )
        for item in results.get("files", []):
            if item["mimeType"] == "application/vnd.google-apps.folder":
                downloaded_paths.extend(
                    download_folder_recursive(drive_service, item["id"], local_path, title_prefix)
                )
            else:
                full_path = get_organized_path(local_path, item["name"])
                downloaded = download_file_direct(drive_service, item["id"], full_path, title_prefix)
                if downloaded:
                    downloaded_paths.append(downloaded)
    except Exception as e:
        print(f"[Error] Recursive fail: {e}")
    return downloaded_paths


def download_with_prefix(drive_service, file_id: str, folder_path: str, prefix: str) -> list[str]:
    try:
        meta = drive_service.files().get(fileId=file_id, fields="mimeType, name").execute()
        original_name = meta.get("name")
        if meta.get("mimeType") == "application/vnd.google-apps.folder":
            return download_folder_recursive(drive_service, file_id, folder_path, prefix)
        full_path = get_organized_path(folder_path, original_name)
        downloaded = download_file_direct(drive_service, file_id, full_path, prefix)
        return [downloaded] if downloaded else []
    except Exception as e:
        print(f"[Error] In download_with_prefix: {e}")
        return []


def extract_audio_from_video(video_path: str, output_audio_path: str) -> str | None:
    import subprocess
    try:
        subprocess.run(
            [
                "ffmpeg", "-i", video_path,
                "-vn", "-ac", "1", "-ar", "44100", "-ab", "128k",
                "-f", "mp3", output_audio_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return output_audio_path
    except Exception as e:
        print(f"[FFmpeg Error] {e}")
        return None
