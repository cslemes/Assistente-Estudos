"""
Video Class Auto-Cutter
========================
Pipeline: Transcrição (JSON Deepgram ou TXT custom) + Silero VAD
→ corte de silêncio, fillers, repetições, pausas longas
→ mp4 final limpo + transcrição remapeada (.json + .txt)

Dependências:
    pip install silero-vad torch torchaudio rapidfuzz

Uso:
    # Preview (não exporta vídeo)
    python video_cutter.py --video aula.mp4 --audio aula.wav --transcript aula.json --preview

    # Exportação completa
    python video_cutter.py --video aula.mp4 --audio aula.wav --transcript aula.json

    # Forçar formato (caso auto-detect falhe)
    python video_cutter.py ... --transcript-format json
    python video_cutter.py ... --transcript-format txt
"""

import re
import argparse
import json
import subprocess
import tempfile
import os
from pathlib import Path
from dataclasses import dataclass

import torch
from rapidfuzz import fuzz


# ─────────────────────────────────────────────
# CONFIGURAÇÃO GLOBAL
# ─────────────────────────────────────────────
CONFIG = {
    # VAD
    "vad_threshold": 0.4,  # 0.0–1.0 — mais alto = mais exigente
    "min_speech_ms": 250,  # segmento mínimo de fala a manter (ms)
    "min_silence_ms": 500,  # silêncio mínimo para ser cortável (ms)
    "pad_ms": 80,  # margem de segurança em cada corte (ms)
    # Pausas longas entre chunks da transcrição
    "long_pause_threshold_s": 2.0,
    # Fillers (português BR)
    "filler_patterns": [
        r"\bé+\b",
        r"\beh+\b",
        r"\bah+\b",
        r"\buh+\b",
        r"\bhm+\b",
        r"\btipo\b",
        r"\bsabe\b",
        r"\bcerto\b",
        r"\bentão\b",
        r"\bou seja\b",
        r"\bcomo é que fala\b",
        r"\bcomo\s+se\s+diz\b",
        r"\bvamos\s+dizer\b",
        r"\bpor\s+assim\s+dizer\b",
    ],
    # Repetições
    "repetition_similarity": 85,  # % similaridade (rapidfuzz)
    "repetition_window": 3,  # quantos chunks anteriores comparar
    # Segmento mínimo a manter após splits (evita micro-clips)
    "min_segment_duration_s": 0.3,
}

FILLER_RE = re.compile("|".join(CONFIG["filler_patterns"]), re.IGNORECASE)


# ─────────────────────────────────────────────
# ESTRUTURAS DE DADOS
# ─────────────────────────────────────────────
@dataclass
class Chunk:
    start: float
    end: float
    speaker: str
    text: str
    cut_reason: str = ""  # vazio = manter


@dataclass
class Segment:
    start: float
    end: float


# ─────────────────────────────────────────────
# PARSERS — AUTO-DETECÇÃO DE FORMATO
# ─────────────────────────────────────────────
def parse_transcript(path: str, fmt: str = "auto") -> list[Chunk]:
    """
    Detecta automaticamente o formato ou usa fmt explícito.
    Formatos suportados:
      - json  → Deepgram: [{text, start, end, speaker}, ...]
      - txt   → Custom:   [MM:SS] [Orador N]: texto
    """
    p = Path(path)
    if fmt == "auto":
        fmt = "json" if p.suffix.lower() == ".json" else "txt"

    if fmt == "json":
        return _parse_json(path)
    else:
        return _parse_txt(path)


def _parse_json(path: str) -> list[Chunk]:
    """
    Deepgram format:
    [{"text": "...", "start": 2.96, "end": 4.72, "speaker": 0}, ...]
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    chunks = []
    for item in raw:
        chunks.append(
            Chunk(
                start=float(item["start"]),
                end=float(item["end"]),
                speaker=str(item.get("speaker", "0")),
                text=item["text"].strip(),
            )
        )
    # Garante ordenação por start
    chunks.sort(key=lambda c: c.start)
    print(f"[transcript] JSON — {len(chunks)} chunks carregados")
    return chunks


def _parse_txt(path: str) -> list[Chunk]:
    """
    Custom format:
    [MM:SS] [Orador N]: texto
    end = timestamp do próximo chunk (ou start + 3s)
    """
    pattern = re.compile(r"\[(\d{1,2}):(\d{2})\]\s*\[([^\]]+)\]:\s*(.+)")
    raw = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = pattern.match(line.strip())
        if m:
            mm, ss, speaker, text = m.groups()
            raw.append((int(mm) * 60 + int(ss), speaker, text.strip()))

    chunks = []
    for i, (start, speaker, text) in enumerate(raw):
        end = raw[i + 1][0] if i + 1 < len(raw) else start + 3.0
        end = max(end, start + 0.5)
        chunks.append(
            Chunk(start=float(start), end=float(end), speaker=speaker, text=text)
        )

    print(f"[transcript] TXT — {len(chunks)} chunks carregados")
    return chunks


# ─────────────────────────────────────────────
# SILERO VAD
# ─────────────────────────────────────────────
def run_vad(audio_path: str) -> list[dict]:
    """Retorna lista de {'start': s, 'end': s} com segmentos de fala."""
    print("[vad] Carregando modelo Silero VAD...")
    model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        force_reload=False,
    )
    (get_speech_timestamps, _, read_audio, *_) = utils

    wav = read_audio(audio_path, sampling_rate=16000)
    print(f"[vad] Áudio: {wav.shape[-1] / 16000:.1f}s")

    timestamps = get_speech_timestamps(
        wav,
        model,
        sampling_rate=16000,
        threshold=CONFIG["vad_threshold"],
        min_speech_duration_ms=CONFIG["min_speech_ms"],
        min_silence_duration_ms=CONFIG["min_silence_ms"],
        speech_pad_ms=CONFIG["pad_ms"],
        return_seconds=True,
    )
    print(f"[vad] {len(timestamps)} segmentos de fala detectados")
    return timestamps


# ─────────────────────────────────────────────
# ANÁLISE DA TRANSCRIÇÃO
# ─────────────────────────────────────────────
def detect_fillers(chunks: list[Chunk]) -> None:
    for chunk in chunks:
        t = chunk.text.strip(" .,;:")
        if FILLER_RE.fullmatch(t):
            chunk.cut_reason = "filler"
        elif len(t.split()) <= 3 and FILLER_RE.search(t):
            if len(FILLER_RE.sub("", t).strip()) <= 2:
                chunk.cut_reason = "filler"


def detect_repetitions(chunks: list[Chunk]) -> None:
    window = CONFIG["repetition_window"]
    threshold = CONFIG["repetition_similarity"]
    for i, chunk in enumerate(chunks):
        if chunk.cut_reason:
            continue
        for j in range(max(0, i - window), i):
            prev = chunks[j]
            if prev.cut_reason:
                continue
            score = fuzz.ratio(chunk.text.lower(), prev.text.lower())
            if score >= threshold:
                chunk.cut_reason = f"repetição (sim={score:.0f}% com chunk {j})"
                break


def detect_long_pauses(chunks: list[Chunk]) -> list[tuple[float, float]]:
    threshold = CONFIG["long_pause_threshold_s"]
    pauses = []
    for i in range(1, len(chunks)):
        gap_start = chunks[i - 1].end
        gap_end = chunks[i].start
        if (gap_end - gap_start) > threshold:
            pauses.append((gap_start + 0.1, gap_end - 0.1))
            print(
                f"[pause] Gap {gap_end - gap_start:.1f}s em {gap_start:.1f}s–{gap_end:.1f}s"
            )
    return pauses


# ─────────────────────────────────────────────
# COMBINAÇÃO VAD + TRANSCRIÇÃO → SEGMENTOS FINAIS
# ─────────────────────────────────────────────
def build_keep_segments(
    vad_segments: list[dict],
    chunks: list[Chunk],
    long_pauses: list[tuple[float, float]],
) -> list[Segment]:
    keep: list[Segment] = [Segment(s["start"], s["end"]) for s in vad_segments]

    remove_regions: list[tuple[float, float]] = [
        (c.start, c.end) for c in chunks if c.cut_reason
    ]
    remove_regions.extend(long_pauses)

    for rem_start, rem_end in remove_regions:
        new_keep = []
        for seg in keep:
            if rem_end <= seg.start or rem_start >= seg.end:
                new_keep.append(seg)
            else:
                if seg.start < rem_start:
                    new_keep.append(Segment(seg.start, rem_start))
                if seg.end > rem_end:
                    new_keep.append(Segment(rem_end, seg.end))
        keep = new_keep

    min_dur = CONFIG["min_segment_duration_s"]
    keep = [s for s in keep if (s.end - s.start) >= min_dur]
    print(f"[segments] {len(keep)} segmentos a manter")
    return keep


# ─────────────────────────────────────────────
# REMAPEAMENTO DA TRANSCRIÇÃO
# ─────────────────────────────────────────────
def remap_transcript(
    chunks: list[Chunk],
    keep_segments: list[Segment],
    output_stem: str,
) -> None:
    """
    Recalcula start/end de cada chunk com base nos segmentos mantidos.

    Lógica:
      Para cada chunk não cortado, verifica em qual keep_segment ele cai.
      O novo timestamp é:
        offset_acumulado_dos_segmentos_anteriores
        + (chunk.start - keep_segment.start)

    Exporta:
      <output_stem>_transcript.json  — mesmo formato Deepgram
      <output_stem>_transcript.txt   — formato legível [MM:SS]
    """
    # Pré-calcula offset acumulado de cada segmento
    # offset[i] = soma das durações dos segmentos 0..i-1
    cum_offset = []
    acc = 0.0
    for seg in keep_segments:
        cum_offset.append(acc)
        acc += seg.end - seg.start

    remapped = []
    for chunk in chunks:
        if chunk.cut_reason:
            continue  # chunk foi cortado, não entra na nova transcrição

        # Encontra o keep_segment que contém este chunk
        new_start = new_end = None
        for idx, seg in enumerate(keep_segments):
            # chunk precisa ter overlap com o segmento
            if chunk.end <= seg.start or chunk.start >= seg.end:
                continue

            # Clipa o chunk dentro dos limites do segmento
            clipped_start = max(chunk.start, seg.start)
            clipped_end = min(chunk.end, seg.end)

            new_start = cum_offset[idx] + (clipped_start - seg.start)
            new_end = cum_offset[idx] + (clipped_end - seg.start)
            break

        if new_start is None:
            # Chunk ficou em região removida pelo VAD — pula
            continue

        remapped.append(
            {
                "text": chunk.text,
                "start": round(new_start, 4),
                "end": round(new_end, 4),
                "speaker": int(chunk.speaker)
                if chunk.speaker.isdigit()
                else chunk.speaker,
            }
        )

    # ── Salva JSON ──
    json_path = f"{output_stem}_transcript.json"
    Path(json_path).write_text(
        json.dumps(remapped, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[remap] ✓ JSON salvo: {json_path}")

    # ── Salva TXT legível ──
    txt_path = f"{output_stem}_transcript.txt"
    lines = []
    for item in remapped:
        total_s = int(item["start"])
        mm, ss = divmod(total_s, 60)
        speaker_label = f"Orador {item['speaker']}"
        lines.append(f"[{mm:02d}:{ss:02d}] [{speaker_label}]: {item['text']}")
    Path(txt_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"[remap] ✓ TXT salvo:  {txt_path}")

    # Estatísticas
    total_original = sum(1 for c in chunks if not c.cut_reason)
    print(f"[remap] {len(remapped)}/{total_original} chunks remapeados")


# ─────────────────────────────────────────────
# EXPORTAÇÃO COM FFMPEG (concat demuxer)
# ─────────────────────────────────────────────
def export_video(
    input_video: str,
    segments: list[Segment],
    output_path: str,
) -> None:
    """
    Exporta os segmentos mantidos como um único mp4.

    Estratégia de PTS:
      Cada clipe é re-encodado (libx264 + aac) com filtros
      setpts=PTS-STARTPTS e asetpts=PTS-STARTPTS para zerar
      os timestamps internos antes do concat. Isso evita o
      problema de áudio/vídeo deslocado que ocorre com -c:v copy
      quando os clipes têm PTS não-zero (e.g. start_pts=138144).
    """
    if not segments:
        print("[export] Nenhum segmento para exportar!")
        return

    print(f"[export] Gerando {len(segments)} clipes temporários...")
    tmp_dir = Path(tempfile.mkdtemp())
    list_file = tmp_dir / "concat.txt"
    clip_files = []

    try:
        for i, seg in enumerate(segments):
            clip_path = str(tmp_dir / f"clip_{i:04d}.mp4")
            clip_files.append(clip_path)
            duration = seg.end - seg.start
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-loglevel",
                    "error",
                    "-ss",
                    str(seg.start),
                    "-i",
                    input_video,
                    "-t",
                    str(duration),
                    # Reseta PTS de vídeo e áudio para 0 em cada clipe
                    "-vf",
                    "setpts=PTS-STARTPTS",
                    "-af",
                    "asetpts=PTS-STARTPTS",
                    # Re-encoda para garantir keyframe no início de cada clipe
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "18",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-movflags",
                    "+faststart",
                    clip_path,
                ],
                check=True,
            )

        with open(list_file, "w") as f:
            for cp in clip_files:
                f.write(f"file '{cp}'\n")

        # Concat final — agora todos os clipes começam em PTS=0
        # então -c copy é seguro aqui
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "warning",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                output_path,
            ],
            check=True,
        )
        print(f"[export] ✓ Vídeo salvo: {output_path}")

    finally:
        list_file.unlink(missing_ok=True)
        for cp in clip_files:
            try:
                os.remove(cp)
            except Exception:
                pass
        try:
            tmp_dir.rmdir()
        except Exception:
            pass


# ─────────────────────────────────────────────
# PREVIEW
# ─────────────────────────────────────────────
def print_preview(chunks: list[Chunk], segments: list[Segment]) -> None:
    print("\n" + "═" * 60)
    print("CHUNKS MARCADOS PARA CORTE")
    print("═" * 60)
    cut_chunks = [c for c in chunks if c.cut_reason]
    if cut_chunks:
        for c in cut_chunks:
            print(f"  [{c.start:.2f}s–{c.end:.2f}s] '{c.text}' → {c.cut_reason}")
    else:
        print("  (nenhum chunk marcado pela transcrição)")

    print("\n" + "═" * 60)
    print("SEGMENTOS MANTIDOS NO VÍDEO FINAL")
    print("═" * 60)
    total_kept = sum(s.end - s.start for s in segments)
    for seg in segments:
        print(f"  {seg.start:.2f}s → {seg.end:.2f}s  ({seg.end - seg.start:.2f}s)")

    if chunks:
        total_orig = chunks[-1].end - chunks[0].start
        pct = 100 * (1 - total_kept / total_orig) if total_orig > 0 else 0
        print(f"\n  Duração mantida:  {total_kept:.1f}s")
        print(f"  Corte estimado:   {pct:.1f}% do conteúdo removido")
    print("═" * 60 + "\n")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Auto-corte de videoaula com remapeamento de transcrição"
    )
    parser.add_argument("--video", required=True, help="Vídeo de entrada (.mp4)")
    parser.add_argument("--audio", default=None, help="Áudio mono 16kHz (.wav) — extraído automaticamente se omitido")
    parser.add_argument(
        "--transcript", required=True, help="Transcrição (.json ou .txt)"
    )
    parser.add_argument(
        "--transcript-format",
        default="auto",
        choices=["auto", "json", "txt"],
        help="Formato da transcrição (padrão: auto)",
    )
    parser.add_argument("--output", default="aula_editada.mp4", help="Vídeo de saída")
    parser.add_argument(
        "--preview", action="store_true", help="Mostra o que seria cortado sem exportar"
    )
    args = parser.parse_args()

    # Stem para os arquivos de transcrição remapeada
    output_stem = str(Path(args.output).with_suffix(""))

    # 1. Parse
    chunks = parse_transcript(args.transcript, fmt=args.transcript_format)

    # 2. VAD — extract audio if not provided
    audio_path = args.audio
    _tmp_wav = None
    if not audio_path:
        import tempfile
        _tmp_wav = tempfile.mktemp(suffix=".wav")
        print(f"[audio] Extraindo áudio de {args.video} → {_tmp_wav}")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", args.video,
             "-ac", "1", "-ar", "16000", "-vn", _tmp_wav],
            check=True,
        )
        audio_path = _tmp_wav

    vad_segments = run_vad(audio_path)

    if _tmp_wav:
        try:
            os.remove(_tmp_wav)
        except OSError:
            pass

    # 3. Análise
    detect_fillers(chunks)
    detect_repetitions(chunks)
    long_pauses = detect_long_pauses(chunks)

    # 4. Segmentos finais
    keep_segments = build_keep_segments(vad_segments, chunks, long_pauses)

    # 5. Preview
    print_preview(chunks, keep_segments)

    if args.preview:
        print("[preview] Modo preview ativo — nada foi exportado.")
        print("          Remova --preview para exportar.")
        return

    # 6. Exporta vídeo
    export_video(args.video, keep_segments, args.output)

    # 7. Remapeia transcrição → novos timestamps
    remap_transcript(chunks, keep_segments, output_stem)


if __name__ == "__main__":
    main()
