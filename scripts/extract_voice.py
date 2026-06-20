"""
Extract clean voice segments for a single speaker from a Deepgram utterances JSON
and concatenate them into a single audio file suitable for ElevenLabs voice cloning.

Usage:
    python scripts/extract_voice.py <audio.mp3> [--json <utterances.json>]
                                                 [--speaker <id>]
                                                 [--minutes <N>]
                                                 [--output <out.mp3>]
                                                 [--min-seg <secs>]

Defaults:
    --json      same path as audio with .json extension
    --speaker   dominant speaker (most total speaking time)
    --minutes   5  (target output duration)
    --output    <audio_stem>_voice.mp3
    --min-seg   3  (skip utterances shorter than N seconds)
"""

import argparse
import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path


def load_utterances(json_path: Path) -> list[dict]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    # Deepgram nested format
    return data.get("utterances", data.get("results", {}).get("utterances", []))


def dominant_speaker(utterances: list[dict]) -> int:
    totals: dict[int, float] = defaultdict(float)
    for u in utterances:
        spk = u.get("speaker", u.get("speaker_id", 0))
        totals[int(spk)] += u.get("end", 0) - u.get("start", 0)
    return max(totals, key=lambda k: totals[k])


def merge_segments(segs: list[tuple[float, float]], gap: float = 0.3) -> list[tuple[float, float]]:
    """Merge segments separated by less than `gap` seconds."""
    if not segs:
        return []
    merged = [segs[0]]
    for start, end in segs[1:]:
        if start - merged[-1][1] <= gap:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def select_segments(
    segs: list[tuple[float, float]],
    target_secs: float,
    min_seg: float,
) -> list[tuple[float, float]]:
    """Pick the longest segments first until we reach target duration."""
    # Filter short segments
    candidates = [(s, e) for s, e in segs if e - s >= min_seg]
    # Sort longest-first so we get the clearest stretches
    candidates.sort(key=lambda x: -(x[1] - x[0]))
    selected = []
    total = 0.0
    for seg in candidates:
        if total >= target_secs:
            break
        selected.append(seg)
        total += seg[1] - seg[0]
    # Restore chronological order for natural-sounding output
    selected.sort(key=lambda x: x[0])
    return selected, total


def ffmpeg_extract(audio: Path, start: float, end: float, out: Path) -> bool:
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", str(start),
            "-to", str(end),
            "-i", str(audio),
            "-ac", "1",          # mono
            "-ar", "44100",      # 44.1 kHz
            "-ab", "192k",       # 192 kbps
            str(out),
        ],
        capture_output=True,
    )
    return result.returncode == 0


def ffmpeg_concat(parts: list[Path], output: Path) -> bool:
    list_file = output.parent / "_concat_list.txt"
    list_file.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in parts),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output),
        ],
        capture_output=True,
    )
    list_file.unlink(missing_ok=True)
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("audio", type=Path, help="Source audio file (.mp3 / .wav)")
    parser.add_argument("--json", type=Path, default=None, help="Utterances JSON (default: audio stem + .json)")
    parser.add_argument("--speaker", type=int, default=None, help="Speaker ID to extract (default: dominant)")
    parser.add_argument("--minutes", type=float, default=5.0, help="Target output duration in minutes (default: 5)")
    parser.add_argument("--output", type=Path, default=None, help="Output file (default: <stem>_voice.mp3)")
    parser.add_argument("--min-seg", type=float, default=3.0, help="Minimum segment length in seconds (default: 3)")
    args = parser.parse_args()

    audio = args.audio.resolve()
    if not audio.exists():
        sys.exit(f"ERROR: audio not found: {audio}")

    json_path = args.json or audio.with_suffix(".json")
    if not json_path.exists():
        sys.exit(f"ERROR: JSON not found: {json_path}")

    output = args.output or audio.parent / f"{audio.stem}_voice.mp3"

    print(f"  Audio  : {audio.name}")
    print(f"  JSON   : {json_path.name}")

    utterances = load_utterances(json_path)
    print(f"  Utterances: {len(utterances)}")

    speaker_id = args.speaker if args.speaker is not None else dominant_speaker(utterances)
    print(f"  Speaker: {speaker_id}")

    # Collect segments for chosen speaker
    raw_segs = [
        (u["start"], u["end"])
        for u in utterances
        if int(u.get("speaker", u.get("speaker_id", 0))) == speaker_id
    ]
    merged = merge_segments(sorted(raw_segs))
    target_secs = args.minutes * 60
    selected, actual_secs = select_segments(merged, target_secs, args.min_seg)

    print(f"  Raw segments   : {len(raw_segs)}")
    print(f"  Merged segments: {len(merged)}")
    print(f"  Selected       : {len(selected)} segments  ({actual_secs:.0f}s / {actual_secs/60:.1f} min)")
    print()

    if not selected:
        sys.exit("ERROR: no segments found for this speaker.")

    # Extract each segment to a temp file
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        parts: list[Path] = []
        for i, (start, end) in enumerate(selected):
            part = tmp_dir / f"part_{i:04d}.mp3"
            ok = ffmpeg_extract(audio, start, end, part)
            if ok:
                parts.append(part)
                print(f"  [{i+1:3d}/{len(selected)}] {start:.1f}s – {end:.1f}s  ({end-start:.1f}s)", end="\r")
            else:
                print(f"  WARNING: failed to extract segment {i} ({start:.1f}–{end:.1f}s)")

        print(f"\n  Concatenating {len(parts)} parts → {output.name} ...")
        ok = ffmpeg_concat(parts, output)

    if ok and output.exists():
        size_mb = output.stat().st_size / (1024 * 1024)
        print(f"\n  Done: {output}")
        print(f"  Size: {size_mb:.1f} MB  |  Duration: ~{actual_secs/60:.1f} min")
        print()
        print("  Ready for ElevenLabs → Professional Voice Cloning → upload this file")
    else:
        sys.exit("ERROR: ffmpeg concat failed.")


if __name__ == "__main__":
    main()
