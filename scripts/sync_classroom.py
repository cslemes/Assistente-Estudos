#!/usr/bin/env python3
"""
Standalone sync script — downloads all materials from Google Classroom to Downloads/.

Runs independently of the API server. Requires credentials.json in the project root.

Usage:
    python scripts/sync_classroom.py                  # sync all courses
    python scripts/sync_classroom.py --course "DL"    # filter by course name substring
    python scripts/sync_classroom.py --dry-run        # list what would be downloaded (no files written)
    python scripts/sync_classroom.py --scrape <url>   # download from a specific Drive/Forms URL
"""

import argparse
import os
import sys

# Allow running from project root without installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")


def cmd_sync(args):
    from app.services.drive import clean_filename, download_with_prefix, get_drive_links_from_form
    from app.services.google_auth import get_google_services

    classroom, drive, _ = get_google_services()

    courses = classroom.courses().list().execute().get("courses", [])
    if args.course:
        courses = [c for c in courses if args.course.lower() in c["name"].lower()]
        if not courses:
            print(f"No courses matching '{args.course}'")
            return

    print(f"Found {len(courses)} course(s)")
    total_files = 0
    downloads_root = os.path.join(os.getcwd(), "Downloads")

    for course in courses:
        c_name = clean_filename(course["name"])
        print(f"\n=== {c_name} ===")
        course_root = os.path.join(downloads_root, c_name)

        topics_res = classroom.courses().topics().list(courseId=course["id"]).execute()
        topic_map = {
            t["topicId"]: clean_filename(t["name"])
            for t in topics_res.get("topic", [])
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
        except Exception as e:
            print(f"  [Warning] Could not list items: {e}")

        for item in items:
            topic_folder = topic_map.get(item.get("topicId"), "General")
            topic_path = os.path.join(course_root, topic_folder)
            prefix = clean_filename((item.get("title") or item.get("text", "Activity"))[:30]).strip()

            print(f"  [{topic_folder}] {prefix}")

            if args.dry_run:
                continue

            os.makedirs(topic_path, exist_ok=True)

            for attachment in item.get("materials", []):
                if "driveFile" in attachment:
                    f_id = attachment["driveFile"]["driveFile"]["id"]
                    paths = download_with_prefix(drive, f_id, topic_path, prefix)
                    total_files += len(paths)

                if "link" in attachment:
                    url = attachment["link"]["url"]
                    if "forms.gle" in url or "docs.google.com/forms" in url:
                        found_ids = get_drive_links_from_form(url)
                        for d_id in found_ids:
                            paths = download_with_prefix(drive, d_id, topic_path, prefix)
                            total_files += len(paths)

    if args.dry_run:
        print("\n[dry-run] No files written.")
    else:
        print(f"\nDone. {total_files} file(s) downloaded to Downloads/")


def cmd_scrape(args):
    from app.services.drive import download_with_prefix, get_drive_links_from_form
    from app.services.google_auth import get_google_services

    print(f"Scraping: {args.url}")
    ids = get_drive_links_from_form(args.url)
    print(f"Found {len(ids)} Drive ID(s)")

    if not ids:
        return

    _, drive, _ = get_google_services()
    dest = args.dest or os.path.join(os.getcwd(), "Downloads", "scraped")
    os.makedirs(dest, exist_ok=True)

    total = 0
    for drive_id in ids:
        paths = download_with_prefix(drive, drive_id, dest, prefix="")
        total += len(paths)

    print(f"Done. {total} file(s) downloaded to {dest}")


def main():
    parser = argparse.ArgumentParser(description="Sync Google Classroom materials to Downloads/")
    sub = parser.add_subparsers(dest="command")

    p_sync = sub.add_parser("sync", help="Sync all courses (default)")
    p_sync.add_argument("--course", help="Filter by course name substring")
    p_sync.add_argument("--dry-run", action="store_true", help="List items without downloading")

    p_scrape = sub.add_parser("scrape", help="Download from a Drive/Forms URL")
    p_scrape.add_argument("url", help="Drive folder or Forms URL")
    p_scrape.add_argument("--dest", help="Destination folder (default: Downloads/scraped)")

    args = parser.parse_args()

    # Default to sync if no subcommand given
    if args.command is None:
        args.command = "sync"
        args.course = None
        args.dry_run = False

    if args.command == "sync":
        cmd_sync(args)
    elif args.command == "scrape":
        cmd_scrape(args)


if __name__ == "__main__":
    main()
