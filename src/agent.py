import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .config import settings
from .video_processor import (
    extract_audio, extract_frames, get_video_duration, get_video_info,
    frame_index_to_timestamp
)
from .verbx_client import get_verbx_client
from .database import log_run


@dataclass
class VideoContext:
    """Aggregated understanding of a video."""
    video_path: str
    duration: float
    transcript_segments: List[Dict[str, Any]]      # STT results
    ocr_results: List[Dict[str, Any]]              # OCR per frame
    scene_descriptions: List[Dict[str, Any]]       # Image Assistant per frame
    fps: float


def process_video(video_path: str, work_dir: str) -> VideoContext:
    """Full pipeline: video → audio + frames → VerbX APIs → aggregated context."""
    verbx = get_verbx_client()
    video_info = get_video_info(video_path)
    duration = video_info["duration"]
    fps = video_info["fps"] or 1.0

    # 1. Extract audio & frames
    audio_path = str(Path(work_dir) / "audio.wav")
    frames_dir = str(Path(work_dir) / "frames")
    extract_audio(video_path, audio_path)
    frame_paths = extract_frames(video_path, frames_dir, fps=1.0)  # 1 fps for demo

    # 2. STT on audio
    stt_result = verbx.stt(audio_path)
    transcript_segments = stt_result.get("segments", [])
    # If no segments found, note it (guardrail: state when something cannot be heard)
    if not transcript_segments:
        transcript_segments = []  # Explicitly empty — agent will report "cannot hear"

    # 3. OCR on each frame
    ocr_results = []
    for i, fp in enumerate(frame_paths):
        ts = frame_index_to_timestamp(i, 1.0)  # 1 fps
        ocr = verbx.ocr(fp)
        ocr["frame_index"] = i
        ocr["timestamp"] = ts
        ocr_results.append(ocr)

    # 4. Image Assistant on each frame
    scene_descriptions = []
    for i, fp in enumerate(frame_paths):
        ts = frame_index_to_timestamp(i, 1.0)
        scene = verbx.image_assistant(fp, "Describe this video frame: scenes, objects, text, actions.")
        scene["frame_index"] = i
        scene["timestamp"] = ts
        scene_descriptions.append(scene)

    return VideoContext(
        video_path=video_path,
        duration=duration,
        transcript_segments=transcript_segments,
        ocr_results=ocr_results,
        scene_descriptions=scene_descriptions,
        fps=1.0,
    )


def _question_intent(question: str) -> Dict[str, bool]:
    """Detect what the question is asking about to guide evidence retrieval."""
    q = question.lower()
    # Dialogue/audio intent keywords
    audio_kw = {"say", "said", "speak", "spoke", "hear", "heard", "tell", "told",
                "mention", "talk", "voice", "dialogue", "conversation", "audio",
                "word", "orateur", "dit", "parle"}
    # Visual text intent keywords
    text_kw = {"text", "read", "written", "write", "screen", "display", "sign",
               "title", "subtitle", "caption", "label", "letter", "word", "texte"}
    # Scene/visual intent keywords
    scene_kw = {"see", "seen", "show", "shown", "look", "scene", "happen",
                "appear", "visible", "watch", "action", "doing", "object",
                "person", "color", "background", "image", "video"}
    words = set(q.split())
    return {
        "audio": bool(words & audio_kw),
        "text": bool(words & text_kw),
        "scene": bool(words & scene_kw),
    }


def find_relevant_context(ctx: VideoContext, question: str) -> Dict[str, Any]:
    """
    Intent-aware relevance matching. Detects what the question asks about
    (dialogue, on-screen text, scenes) and returns all matching evidence.
    Falls back to keyword overlap when intent doesn't match.
    """
    q_lower = question.lower()
    q_words = [w for w in q_lower.split() if len(w) > 2]
    intent = _question_intent(question)
    relevant = {"transcript": [], "ocr": [], "scenes": []}

    # --- Transcript / dialogue ---
    for seg in ctx.transcript_segments:
        text = seg.get("text", "").lower()
        # Include if question is about dialogue OR keyword overlap
        keyword_hit = any(w in text for w in q_words)
        if intent["audio"] or keyword_hit:
            relevant["transcript"].append({
                "text": seg.get("text"),
                "start": seg.get("start"),
                "end": seg.get("end"),
            })

    # --- OCR / on-screen text ---
    seen_ocr_texts = set()
    for ocr in ctx.ocr_results:
        for block in ocr.get("output", {}).get("blocks", []):
            text = block.get("text", "").strip()
            if not text or text.lower() in ("", "ocr unavailable (api error)") or text.lower().startswith("i'm sorry"):
                continue
            # Deduplicate identical OCR across frames
            text_key = text.lower()
            if text_key in seen_ocr_texts:
                continue
            seen_ocr_texts.add(text_key)
            keyword_hit = any(w in text.lower() for w in q_words)
            if intent["text"] or keyword_hit:
                relevant["ocr"].append({
                    "text": text,
                    "timestamp": ocr.get("timestamp"),
                    "frame_index": ocr.get("frame_index"),
                })

    # --- Scene descriptions ---
    for scene in ctx.scene_descriptions:
        desc = scene.get("output", {}).get("description", "")
        if not desc or desc.lower().startswith("frame processed"):
            continue
        keyword_hit = any(w in desc.lower() for w in q_words)
        if intent["scene"] or keyword_hit:
            relevant["scenes"].append({
                "description": desc,
                "timestamp": scene.get("timestamp"),
                "frame_index": scene.get("frame_index"),
            })

    # Fallback: if nothing matched via intent, try loose keyword matching
    if not any(relevant.values()):
        for seg in ctx.transcript_segments:
            text = seg.get("text", "")
            if text.strip():
                relevant["transcript"].append({
                    "text": text, "start": seg.get("start"), "end": seg.get("end"),
                })
        for ocr in ctx.ocr_results:
            for block in ocr.get("output", {}).get("blocks", []):
                text = block.get("text", "").strip()
                if text and text.lower() != "ocr unavailable (api error)":
                    relevant["ocr"].append({
                        "text": text,
                        "timestamp": ocr.get("timestamp"),
                        "frame_index": ocr.get("frame_index"),
                    })

    return relevant


def generate_answer(ctx: VideoContext, question: str, target_lang: str) -> Dict[str, Any]:
    """
    Generate answer from relevant context.
    In production: use LLM. Here: template-based for demo determinism.
    """
    relevant = find_relevant_context(ctx, question)
    verbx = get_verbx_client()

    # Build evidence
    evidence = []
    answer_parts = []
    timestamps = {"dialogue": [], "ocr": [], "scenes": []}

    # Dialogue evidence
    for t in relevant["transcript"]:
        start = t.get("start") or 0.0
        end = t.get("end") or 0.0
        answer_parts.append(f"[Dialogue @ {start:.1f}-{end:.1f}s] {t['text']}")
        timestamps["dialogue"].append({"start": start, "end": end, "text": t["text"]})
        evidence.append({"type": "stt", "input_ref": ctx.video_path, "output": t})

    # OCR evidence
    for o in relevant["ocr"]:
        answer_parts.append(f"[On-screen text @ {o['timestamp']:.1f}s] {o['text']}")
        timestamps["ocr"].append({"timestamp": o["timestamp"], "text": o["text"]})
        evidence.append({"type": "ocr", "input_ref": ctx.video_path, "output": o})

    # Scene evidence
    for s in relevant["scenes"]:
        answer_parts.append(f"[Scene @ {s['timestamp']:.1f}s] {s['description']}")
        timestamps["scenes"].append({"timestamp": s["timestamp"], "description": s["description"]})
        evidence.append({"type": "image_assist", "input_ref": ctx.video_path, "output": s})

    # Determine status
    if not any(relevant.values()):
        status = "uncertain"
        answer_text = "I cannot see or hear the relevant content in the video to answer this question."
    elif not relevant["transcript"] and not relevant["ocr"] and not relevant["scenes"]:
        status = "partial"
        answer_text = "I found some related content but cannot give a precise answer."
    else:
        status = "success"
        answer_text = " ".join(answer_parts[:3])  # Limit for demo

    # Translate if needed
    if target_lang != "en":
        trans = verbx.translate(answer_text, target_lang)
        answer_text = trans.get("translated_text", answer_text)
        evidence.append({"type": "translation", "input_ref": answer_text, "output": trans})

    return {
        "answer": answer_text,
        "timestamps": timestamps,
        "status": status,
        "evidence": evidence,
        "language": target_lang,
    }


def answer_question(video_path: str, question: str, target_lang: str = "en") -> Dict[str, Any]:
    """Main entry: video + question → answer with timestamps + audio."""
    with tempfile.TemporaryDirectory() as work_dir:
        ctx = process_video(video_path, work_dir)
        result = generate_answer(ctx, question, target_lang)

        # TTS for voice answer
        verbx = get_verbx_client()
        audio_bytes = verbx.tts(result["answer"], result["language"])
        audio_path = str(Path(work_dir) / "answer.wav")
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        # Copy to outputs for demo
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        import uuid
        final_audio = output_dir / f"answer_{uuid.uuid4().hex[:8]}.wav"
        shutil.copy(audio_path, final_audio)

        result["answer_audio_path"] = str(final_audio)
        result["video_path"] = video_path
        result["question"] = question

        # Log to DB
        log_run(
            test_case="manual",
            video_path=video_path,
            question=question,
            answer=result["answer"],
            answer_audio_path=str(final_audio),
            timestamps=result["timestamps"],
            language=result["language"],
            status=result["status"],
            evidence=result["evidence"],
        )

        return result