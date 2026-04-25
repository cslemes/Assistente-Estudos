import os

os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.services.drive import SCOPES, clean_filename, download_with_prefix, get_drive_links_from_form


def run_sync():
    print("--- Starting Study Assistant Sync ---")

    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    classroom = build("classroom", "v1", credentials=creds)
    drive = build("drive", "v3", credentials=creds)

    courses = classroom.courses().list().execute().get("courses", [])
    downloaded_count = 0
    downloaded_files = []

    for course in courses:
        c_name = clean_filename(course["name"])
        print(f"\n--- COURSE: {c_name} ---")
        course_root = os.path.join(os.getcwd(), "Downloads", c_name)

        topics_res = classroom.courses().topics().list(courseId=course["id"]).execute()
        topic_map = {
            t["topicId"]: clean_filename(t["name"]) for t in topics_res.get("topic", [])
        }

        items = []
        try:
            items += (
                classroom.courses()
                .courseWork()
                .list(courseId=course["id"])
                .execute()
                .get("courseWork", [])
            )
            items += (
                classroom.courses()
                .courseWorkMaterials()
                .list(courseId=course["id"])
                .execute()
                .get("courseWorkMaterial", [])
            )
        except Exception:
            pass

        for item in items:
            t_id = item.get("topicId")
            topic_folder = topic_map.get(t_id, "General")
            topic_path = os.path.join(course_root, topic_folder)
            os.makedirs(topic_path, exist_ok=True)

            raw_title = item.get("title") or item.get("text", "Activity")
            prefix = clean_filename(raw_title[:30]).strip()

            print(f"   [{topic_folder}] Syncing: {prefix}...")

            for attachment in item.get("materials", []):
                if "driveFile" in attachment:
                    f_id = attachment["driveFile"]["driveFile"]["id"]
                    paths = download_with_prefix(drive, f_id, topic_path, prefix)
                    downloaded_files.extend(paths)
                    downloaded_count += len(paths)

                if "link" in attachment:
                    url = attachment["link"]["url"]
                    if "forms.gle" in url or "docs.google.com/forms" in url:
                        found_ids = get_drive_links_from_form(url)
                        for d_id in found_ids:
                            paths = download_with_prefix(drive, d_id, topic_path, prefix)
                            downloaded_files.extend(paths)
                            downloaded_count += len(paths)

    print("\n--- Sync Complete ---")
    return {
        "courses": len(courses),
        "files_downloaded": downloaded_count,
        "downloaded_files": downloaded_files,
    }
