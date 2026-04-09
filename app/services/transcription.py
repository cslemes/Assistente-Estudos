import json
import os
from dotenv import load_dotenv
from app.database import insert_transcription, has_segments
from app.config.settings import Settings

load_dotenv()
_settings = Settings()


def transcribe_file(file_path: str):
    output_txt = os.path.splitext(file_path)[0] + ".txt"
    output_json = os.path.splitext(file_path)[0] + ".json"

    if os.path.exists(output_txt) and has_segments(file_path):
        print(f"[Transcription] Already transcribed: {os.path.basename(file_path)}")
        return

    provider = _settings.transcription_provider
    if provider == "openai":
        _transcribe_openai(file_path, output_txt, output_json)
    elif provider == "groq":
        _transcribe_groq(file_path, output_txt, output_json)
    else:
        _transcribe_deepgram(file_path, output_txt, output_json)


def _write_outputs(file_path: str, output_txt: str, output_json: str, segments: list[dict], full_text: str):
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(full_text)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    insert_transcription(
        file_path=file_path,
        text=full_text,
        segments_json=json.dumps(segments, ensure_ascii=False),
    )


def _transcribe_deepgram(file_path: str, output_txt: str, output_json: str):
    from deepgram import DeepgramClient

    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        print("[Deepgram Error] No DEEPGRAM_API_KEY found in .env")
        return

    print(f"[Deepgram] Transcribing: {os.path.basename(file_path)}...")
    try:
        deepgram = DeepgramClient(api_key=api_key)

        with open(file_path, "rb") as audio_file:
            response = deepgram.listen.v1.media.transcribe_file(
                request=audio_file.read(),
                model="nova-3",
                smart_format=True,
                language="pt-BR",
                diarize=True,
                utterances=True,
                punctuate=True,
            )

        utterances = response.results.utterances or []
        print(f"[Deepgram] Utterances received: {len(utterances)}, Words: {len(response.results.channels[0].alternatives[0].words)}")

        segments = [
            {
                "text": utt.transcript,
                "start": utt.start,
                "end": utt.end,
                "speaker": getattr(utt, "speaker", 0),
            }
            for utt in utterances
        ]

        lines = [
            f"[{int(s['start'] // 60):02d}:{int(s['start'] % 60):02d}] [Orador {s['speaker']}]: {s['text']}"
            for s in segments
        ]
        full_text = "\n".join(lines)

        _write_outputs(file_path, output_txt, output_json, segments, full_text)
        print(f"[Deepgram] Success! Saved {os.path.basename(output_txt)} and {os.path.basename(output_json)}")

    except Exception as e:
        import traceback
        print(f"[Deepgram Error] Failed to transcribe {file_path}: {e}")
        traceback.print_exc()


def _transcribe_openai(file_path: str, output_txt: str, output_json: str):
    from openai import OpenAI

    if not _settings.openai_api_key:
        print("[OpenAI Whisper Error] No OPENAI_API_KEY found in .env")
        return

    print(f"[OpenAI Whisper] Transcribing: {os.path.basename(file_path)}...")
    try:
        client = OpenAI(api_key=_settings.openai_api_key)

        with open(file_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model=_settings.openai_whisper_model,
                file=f,
                response_format="verbose_json",
                language="pt",
            )

        segments = [
            {"text": s.text, "start": s.start, "end": s.end, "speaker": None}
            for s in response.segments
        ]

        lines = [
            f"[{int(s['start'] // 60):02d}:{int(s['start'] % 60):02d}]: {s['text']}"
            for s in segments
        ]
        full_text = "\n".join(lines)

        _write_outputs(file_path, output_txt, output_json, segments, full_text)
        print(f"[OpenAI Whisper] Success! Saved {os.path.basename(output_txt)} and {os.path.basename(output_json)}")

    except Exception as e:
        import traceback
        print(f"[OpenAI Whisper Error] Failed to transcribe {file_path}: {e}")
        traceback.print_exc()


def _transcribe_groq(file_path: str, output_txt: str, output_json: str):
    from groq import Groq

    if not _settings.Groq_api_key:
        print("[Groq Whisper Error] No GROQ_API_KEY found in .env")
        return

    print(f"[Groq Whisper] Transcribing: {os.path.basename(file_path)}...")
    try:
        client = Groq(api_key=_settings.Groq_api_key)

        with open(file_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model=_settings.groq_whisper_model,
                file=f,
                response_format="verbose_json",
                language="pt",
            )

        segments = [
            {"text": s.text, "start": s.start, "end": s.end, "speaker": None}
            for s in response.segments
        ]

        lines = [
            f"[{int(s['start'] // 60):02d}:{int(s['start'] % 60):02d}]: {s['text']}"
            for s in segments
        ]
        full_text = "\n".join(lines)

        _write_outputs(file_path, output_txt, output_json, segments, full_text)
        print(f"[Groq Whisper] Success! Saved {os.path.basename(output_txt)} and {os.path.basename(output_json)}")

    except Exception as e:
        import traceback
        print(f"[Groq Whisper Error] Failed to transcribe {file_path}: {e}")
        traceback.print_exc()
