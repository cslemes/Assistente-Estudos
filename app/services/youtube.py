import os
from googleapiclient.http import MediaFileUpload


def upload_to_youtube(youtube_service, file_path: str, title: str, description: str = ""):
    marker_file = file_path + ".uploaded"

    if os.path.exists(marker_file):
        print(f"[YouTube] Already uploaded: {os.path.basename(file_path)}")
        return

    print(f"[YouTube] Uploading: {title}")
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["StudyAssistant", "Classroom"],
            "categoryId": "27",
        },
        "status": {"privacyStatus": "unlisted"},
    }

    media = MediaFileUpload(file_path, chunksize=1024 * 1024 * 10, resumable=True)
    request = youtube_service.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"[YouTube] Upload {int(status.progress() * 100)}%")

    video_id = response.get("id")
    with open(marker_file, "w", encoding="utf-8") as f:
        f.write(video_id)

    print(f"[YouTube] Done: https://youtu.be/{video_id}")
