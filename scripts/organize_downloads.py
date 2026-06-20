"""
Rename topic folders inside the downloads directory to add Aula_NN_ prefixes,
then optionally sync the new paths into SQLite and Qdrant.

Phase 1 — regex: extracts Aula number from each topic's video filename.
Phase 2 — LLM:  for topics the regex couldn't number, sends the full course
           topic list to Groq and asks it to infer the missing numbers and
           flag any naming inconsistencies across the course.
Phase 3 — clean: renames raw video files inside video/ subfolders to the
           canonical Aula_NN_Topic.mp4 format, skipping files already clean
           and using _2/_3 suffixes to avoid overwriting existing clips.

Usage:
    python3 scripts/organize_downloads.py                    # dry-run, calls LLM
    python3 scripts/organize_downloads.py --apply            # rename folders + clean videos
    python3 scripts/organize_downloads.py --apply --sync     # rename + update SQLite + Qdrant
    python3 scripts/organize_downloads.py --apply --no-clean # rename folders only
    python3 scripts/organize_downloads.py --sync             # sync only (after manual renames)
    python3 scripts/organize_downloads.py --no-llm           # regex only, no API call
    python3 scripts/organize_downloads.py --base /other/downloads
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

# Make the project root importable so app.* packages resolve correctly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.config.settings import Settings

DEFAULT_BASE = Path(__file__).parent.parent / "downloads"
AULA_RE = re.compile(r"[Aa]ula[_ ]0*(\d+)", re.IGNORECASE)
CLEAN_FILE_RE = re.compile(r"^Aula_\d+_", re.IGNORECASE)

PROMPT_TEMPLATE = """\
You are organizing class recordings for a postgraduate AI course at PUC-Rio.

Course: "{course}"

Topics already numbered (extracted from video filenames):
{numbered}

Topics WITHOUT a detected class number — infer the most likely number for each:
{unnumbered}

Instructions:
1. Infer the class number for each unnumbered topic by reasoning about the
   curriculum sequence, topic names, and gaps in the numbered list.
2. Flag any naming inconsistencies across ALL topics: typos, duplicate concepts
   with slightly different names, topics that seem out of place for this course.

Return ONLY valid JSON, no markdown fences:
{{
  "assignments": {{"<exact topic name>": <integer number>, ...}},
  "inconsistencies": [
    {{"issue": "<description>", "affected": ["<topic name>", ...]}}
  ]
}}

Omit a topic from "assignments" only if you truly cannot determine its number.
"""


def extract_aula_number(topic_dir: Path) -> int | None:
    """Extract Aula number from the first matching .mp4 in the video/ subfolder."""
    video_dir = topic_dir / "video"
    if not video_dir.is_dir():
        return None
    for f in sorted(video_dir.iterdir()):
        if f.suffix.lower() == ".mp4":
            m = AULA_RE.search(f.stem)
            if m:
                return int(m.group(1))
    return None


def already_numbered(name: str) -> bool:
    return bool(re.match(r"Aula_\d+_", name))


def _strip_prefix(name: str) -> str:
    """Return topic name without Aula_NN_ prefix."""
    return re.sub(r"^Aula_\d+_", "", name)


def scan_courses(base: Path) -> tuple[dict[str, dict[str, int | None]], list[tuple[Path, Path]]]:
    """
    Returns:
        courses        — {course_name: {topic_name: number_or_None}}
        merge_pairs    — [(unnumbered_dir, numbered_dir)] for sync-created duplicates
    """
    courses: dict[str, dict[str, int | None]] = {}
    merge_pairs: list[tuple[Path, Path]] = []

    for course in sorted(base.iterdir()):
        if not course.is_dir():
            continue
        topics: dict[str, int | None] = {}
        all_names = [t.name for t in course.iterdir() if t.is_dir()]

        # Build a map of stripped-name → numbered folder for merge detection
        numbered_by_base: dict[str, str] = {}
        for name in all_names:
            if already_numbered(name):
                numbered_by_base[_strip_prefix(name)] = name

        for topic in sorted(course.iterdir()):
            if not topic.is_dir():
                continue
            name = topic.name
            if already_numbered(name):
                m = re.match(r"Aula_(\d+)_", name)
                topics[name] = int(m.group(1)) if m else None
            else:
                # Check if a numbered sibling already exists for this topic
                if name in numbered_by_base:
                    numbered_sibling = course / numbered_by_base[name]
                    merge_pairs.append((topic, numbered_sibling))
                    # Don't add to topics — it will be merged/removed
                    continue
                topics[name] = extract_aula_number(topic)

        courses[course.name] = topics

    return courses, merge_pairs


def call_llm(course: str, numbered: dict[str, int], unnumbered: list[str]) -> dict:
    """Call Groq directly to infer missing numbers and check consistency."""
    from groq import Groq
    settings = Settings()
    client = Groq(api_key=settings.Groq_api_key)

    numbered_lines = "\n".join(
        f"  - Aula {n:02d}: \"{name}\""
        for name, n in sorted(numbered.items(), key=lambda x: x[1])
    ) or "  (none yet)"
    unnumbered_lines = "\n".join(f"  - \"{name}\"" for name in unnumbered)

    prompt = PROMPT_TEMPLATE.format(
        course=course,
        numbered=numbered_lines,
        unnumbered=unnumbered_lines,
    )

    response = client.chat.completions.create(
        model=settings.summarize_groq_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1024,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"  [LLM] Bad JSON for '{course}':\n{raw[:300]}", file=sys.stderr)
        return {"assignments": {}, "inconsistencies": []}


def build_plan(
    base: Path, courses: dict[str, dict[str, int | None]], use_llm: bool
) -> tuple[list[tuple[Path, Path, bool]], list[Path], list[dict]]:
    """
    Returns:
        renames      — (src_path, dst_path, from_llm) pairs
        unresolved   — topic dirs that still have no number after LLM
        issues       — [{"course": str, "inconsistencies": [...]}]
    """
    if use_llm and not Settings().Groq_api_key:
        print("  WARNING: GROQ_API_KEY not set — LLM phase will be skipped.\n")
        use_llm = False

    renames: list[tuple[Path, Path, bool]] = []
    unresolved: list[Path] = []
    issues: list[dict] = []

    for course_name, topics in courses.items():
        course_dir = base / course_name

        numbered = {name: num for name, num in topics.items() if num is not None and not already_numbered(name)}
        unnumbered = [name for name, num in topics.items() if num is None and not already_numbered(name)]

        llm_assignments: dict[str, int] = {}
        llm_inconsistencies: list[dict] = []

        if use_llm and (unnumbered or numbered):
            tag = f"{len(numbered)} numbered, {len(unnumbered)} missing"
            print(f"  [LLM] {course_name!r}  ({tag})")
            sys.stdout.flush()
            result = call_llm(course_name, numbered, unnumbered)
            llm_assignments = result.get("assignments", {})
            llm_inconsistencies = result.get("inconsistencies", [])

        # Regex takes precedence; LLM fills gaps
        all_numbers: dict[str, int] = {**llm_assignments, **numbered}

        llm_sourced: set[str] = set(llm_assignments) - set(numbered)

        for topic_name, num in all_numbers.items():
            src = course_dir / topic_name
            if not src.exists() or already_numbered(topic_name):
                continue
            dst = course_dir / f"Aula_{num:02d}_{topic_name}"
            renames.append((src, dst, topic_name in llm_sourced))

        for topic_name in unnumbered:
            if topic_name not in all_numbers:
                unresolved.append(course_dir / topic_name)

        if llm_inconsistencies:
            issues.append({"course": course_name, "inconsistencies": llm_inconsistencies})

    return sorted(renames, key=lambda r: (r[0].parent.name, r[1].name)), unresolved, issues


def _clean_topic(folder_name: str) -> str:
    """Strip Aula_NN_ prefix so the topic stays display-friendly."""
    return re.sub(r"^Aula_\d+_", "", folder_name)


def _unique_dst(folder: Path, canonical: str) -> Path:
    """Return an available path for canonical inside folder, adding _2/_3 on collision."""
    stem = Path(canonical).stem
    candidate = folder / canonical
    n = 2
    while candidate.exists():
        candidate = folder / f"{stem}_{n}.mp4"
        n += 1
    return candidate


def clean_video_files(topic_dirs: list[Path], dry_run: bool) -> list[tuple[Path, Path]]:
    """
    Phase 3: rename raw video files inside video/ subfolders to Aula_NN_Topic.mp4.

    Skips files already matching Aula_NN_* pattern.
    Uses _2/_3 suffixes if the canonical name is already taken.
    """
    renames: list[tuple[Path, Path]] = []

    for topic_dir in topic_dirs:
        if not topic_dir.is_dir():
            continue
        video_dir = topic_dir / "video"
        if not video_dir.is_dir():
            continue

        m = re.match(r"Aula_(\d+)_(.*)", topic_dir.name)
        if not m:
            continue
        num = int(m.group(1))
        clean_topic = m.group(2)
        canonical = f"Aula_{num:02d}_{clean_topic}.mp4"

        for f in sorted(video_dir.iterdir()):
            if f.suffix.lower() != ".mp4":
                continue
            if CLEAN_FILE_RE.match(f.name):
                continue  # already has Aula_NN_ prefix — skip
            dst = _unique_dst(video_dir, canonical)
            renames.append((f, dst))
            if not dry_run:
                f.rename(dst)

    return renames


def apply_merges(merge_pairs: list[tuple[Path, Path]], dry_run: bool) -> int:
    """
    Move files from unnumbered duplicate folders into the already-numbered sibling,
    then remove the now-empty unnumbered folder.
    Returns count of merged folders.
    """
    count = 0
    for src_dir, dst_dir in merge_pairs:
        src_video = src_dir / "video"
        dst_video = dst_dir / "video"

        if dry_run:
            print(f"    [merge dry] {src_dir.name!r} → {dst_dir.name!r}")
            if src_video.is_dir():
                for f in sorted(src_video.iterdir()):
                    print(f"      move: {f.name}")
            continue

        if src_video.is_dir():
            dst_video.mkdir(parents=True, exist_ok=True)
            for f in sorted(src_video.iterdir()):
                target = dst_video / f.name
                if target.exists():
                    # Avoid collision: add _merge suffix
                    target = _unique_dst(dst_video, f.name if f.suffix.lower() == ".mp4" else f.name)
                shutil.move(str(f), str(target))

        # Remove any remaining subdirs/files from src_dir then the dir itself
        try:
            shutil.rmtree(src_dir)
        except OSError as e:
            print(f"    [merge] WARNING: could not remove {src_dir.name}: {e}")
            continue

        print(f"    [merge] {src_dir.name!r} → {dst_dir.name!r}")
        count += 1

    return count


def sync_sqlite(renames: list, dry_run: bool) -> int:
    """Update file_path in SQLite for every renamed folder."""
    from app.database import get_connection

    total = 0
    with get_connection() as conn:
        rows = conn.execute("SELECT id, file_path FROM transcriptions").fetchall()
        for row in rows:
            old_fp = row["file_path"]
            new_fp = old_fp
            for src, dst, _ in renames:
                # Paths in the DB may use / or \ as separator
                for sep in ("/", "\\"):
                    old_seg = f"{sep}{src.name}{sep}"
                    new_seg = f"{sep}{dst.name}{sep}"
                    if old_seg in new_fp:
                        new_fp = new_fp.replace(old_seg, new_seg)
            if new_fp != old_fp:
                if dry_run:
                    print(f"    [SQLite dry] id={row['id']}")
                    print(f"      {old_fp}")
                    print(f"      → {new_fp}")
                else:
                    conn.execute(
                        "UPDATE transcriptions SET file_path = ? WHERE id = ?",
                        (new_fp, row["id"]),
                    )
                total += 1
    return total


def sync_qdrant(renames: list, settings: Settings, dry_run: bool) -> int:
    """Update file_path and topic in Qdrant for every renamed folder."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    collection = settings.collection_name
    total = 0

    for src, dst, _ in renames:
        old_topic = src.name
        new_topic = dst.name
        clean = _clean_topic(new_topic)

        offset = None
        batch: list[str] = []
        while True:
            points, next_offset = client.scroll(
                collection_name=collection,
                scroll_filter=Filter(
                    must=[FieldCondition(key="topic", match=MatchValue(value=old_topic))]
                ),
                with_payload=["file_path"],
                with_vectors=False,
                limit=200,
                offset=offset,
            )

            for point in points:
                old_fp = point.payload.get("file_path", "")
                new_fp = old_fp
                for sep in ("/", "\\"):
                    old_seg = f"{sep}{old_topic}{sep}"
                    new_seg = f"{sep}{new_topic}{sep}"
                    if old_seg in new_fp:
                        new_fp = new_fp.replace(old_seg, new_seg)

                if dry_run:
                    print(f"    [Qdrant dry] id={point.id}  topic={old_topic!r}→{clean!r}")
                else:
                    try:
                        client.set_payload(
                            collection_name=collection,
                            payload={"file_path": new_fp, "topic": clean},
                            points=[point.id],
                        )
                    except Exception as e:
                        msg = str(e)
                        if "No space left" in msg or "disk" in msg.lower():
                            print(f"  [Qdrant] ✗ Disk full — free space on your Qdrant instance and retry.")
                            return total
                        raise
                batch.append(point.id)

            if next_offset is None:
                break
            offset = next_offset

        if batch:
            verb = "Would update" if dry_run else "Updated"
            print(f"  [Qdrant] {verb} {len(batch)} point(s): {old_topic!r} → {clean!r}")
            total += len(batch)

    return total


def _rename_folder(src: Path, dst: Path) -> None:
    """
    Rename a folder on Windows, working around file-watcher handle locks
    (VS Code, Explorer, antivirus) that block os.rename / Rename-Item.

    Strategy:
      1. os.rename (fast path)
      2. robocopy /MOVE /E — copies files to new dir, deletes source files;
         avoids renaming the directory handle itself so watcher locks don't matter.
    """
    import subprocess, sys

    try:
        src.rename(dst)
        return
    except PermissionError:
        pass

    if sys.platform != "win32":
        print(f"           ✗ FAILED — permission denied (non-Windows, cannot fall back)")
        return

    # robocopy /MOVE copies all files+subdirs into dst, then removes them from src.
    # Exit codes 0-7 are all success variants for robocopy.
    result = subprocess.run(
        ["robocopy", str(src), str(dst), "/E", "/MOVE", "/NFL", "/NDL", "/NJH", "/NJS", "/NC", "/NS"],
        capture_output=True,
    )
    if result.returncode < 8:
        try:
            src.rmdir()  # remove now-empty source directory
        except OSError:
            pass  # already gone or still has a stale watcher handle — harmless
        return

    # All methods exhausted
    err = result.stderr.decode(errors="replace").strip() or result.stdout.decode(errors="replace").strip()
    print(f"           ✗ FAILED — {err or 'all rename methods failed'}")
    print("             Add downloads/ to VS Code's files.watcherExclude setting and retry.")


def print_section(title: str, char: str = "=", width: int = 62) -> None:
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--apply", action="store_true", help="Apply renames (default: dry-run)")
    parser.add_argument("--sync", action="store_true", help="Update SQLite + Qdrant after renaming")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM — regex detection only")
    parser.add_argument("--no-clean", action="store_true", help="Skip Phase 3 video file cleaning")
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE, help="Root downloads directory")
    args = parser.parse_args()

    if not args.base.is_dir():
        print(f"ERROR: directory not found: {args.base}", file=sys.stderr)
        sys.exit(1)

    use_llm = not args.no_llm
    dry_run = not args.apply
    mode = "APPLYING" if args.apply else "DRY-RUN"

    print("\nPhase 1 — scanning directories...")
    courses, merge_pairs = scan_courses(args.base)

    if use_llm:
        print("Phase 2 — calling LLM for missing numbers and consistency check...\n")
        sys.stdout.flush()

    renames, unresolved, issues = build_plan(args.base, courses, use_llm)

    # ── Merge duplicates (sync conflict resolution) ───────────────────────────
    if merge_pairs:
        print_section(f"{mode}  —  {len(merge_pairs)} sync duplicate(s) to merge", char="~")
        apply_merges(merge_pairs, dry_run=dry_run)

    # ── Renames ──────────────────────────────────────────────────────────────
    print_section(f"{mode}  —  {len(renames)} folder renames planned")

    current_course = None
    for src, dst, from_llm in renames:
        if src.parent.name != current_course:
            current_course = src.parent.name
            print(f"\n  [{current_course}]")
        tag = "[LLM  ]" if from_llm else "[regex]"
        print(f"    {tag} {src.name!r}")
        print(f"           → {dst.name!r}")
        if args.apply:
            _rename_folder(src, dst)

    # ── Unresolved ───────────────────────────────────────────────────────────
    if unresolved:
        print_section(f"UNRESOLVED — {len(unresolved)} folders (no number found)", char="-")
        for p in unresolved:
            print(f"  {p.parent.name}/{p.name}")

    # ── Inconsistencies ───────────────────────────────────────────────────────
    if issues:
        print_section("NAMING INCONSISTENCIES FLAGGED BY LLM", char="!")
        for item in issues:
            print(f"\n  Course: {item['course']}")
            for inc in item["inconsistencies"]:
                print(f"    • {inc['issue']}")
                for affected in inc.get("affected", []):
                    print(f"        - {affected}")

    # ── Phase 3: clean video files ────────────────────────────────────────────
    n_cleaned = 0
    if not args.no_clean:
        # Collect all numbered topic dirs: already-numbered (from scan) + just-renamed
        numbered_dirs: list[Path] = []
        for course_name, topic_map in courses.items():
            course_dir = args.base / course_name
            for name in topic_map:
                if already_numbered(name):
                    d = course_dir / name
                    if d.is_dir():
                        numbered_dirs.append(d)
        # Add destinations of this run's renames (now numbered on disk if --apply)
        seen = set(numbered_dirs)
        for _, dst, _ in renames:
            if dst not in seen:
                numbered_dirs.append(dst)
                seen.add(dst)

        if numbered_dirs:
            file_renames = clean_video_files(numbered_dirs, dry_run=dry_run)
            n_cleaned = len(file_renames)
            if file_renames:
                print_section(f"Phase 3 — {mode}  —  {n_cleaned} video file(s) to clean")
                current_parent = None
                for src_f, dst_f in file_renames:
                    parent_label = f"{src_f.parent.parent.parent.name}/{src_f.parent.parent.name}"
                    if parent_label != current_parent:
                        current_parent = parent_label
                        print(f"\n  [{parent_label}]")
                    prefix = "  [dry-run]" if dry_run else "  [clean  ]"
                    print(f"    {prefix} {src_f.name!r}")
                    print(f"              → {dst_f.name!r}")
            else:
                print("\nPhase 3 — all video files already clean.")

    # ── Sync SQLite + Qdrant ─────────────────────────────────────────────────
    n_db = n_q = 0
    if args.sync and renames:
        print_section("SYNC — SQLite + Qdrant" + (" (dry-run)" if dry_run else ""), char="~")

        print("\n  SQLite:")
        n_db = sync_sqlite(renames, dry_run=dry_run)
        print(f"  → {n_db} row(s) {'would be ' if dry_run else ''}updated")

        print("\n  Qdrant:")
        n_q = sync_qdrant(renames, Settings(), dry_run=dry_run)
        print(f"  → {n_q} point(s) {'would be ' if dry_run else ''}updated")

    # ── Footer ───────────────────────────────────────────────────────────────
    print()
    if not args.apply:
        suffix = " --sync" if args.sync else ""
        print(f"Run with --apply{suffix} to execute.")
    else:
        msg = f"Done. {len(renames)} folder(s) renamed, {n_cleaned} video file(s) cleaned."
        if args.sync:
            msg += f"  {n_db} DB row(s) and {n_q} Qdrant point(s) updated."
        print(msg)


if __name__ == "__main__":
    main()
