import os

os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from app.services.drive import clean_filename, download_with_prefix, get_drive_links_from_form
from app.services.google_auth import get_google_services


def run_sync():
    print("--- Starting Study Assistant Sync ---")

    classroom, drive, _ = get_google_services()

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
