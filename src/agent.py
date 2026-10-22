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


def find_relevant_context(ctx: VideoContext, question: str) -> Dict[str, Any]:
    """
    Simple relevance matching: keyword overlap between question and
    transcript/OCR/scene text. Returns relevant segments with timestamps.
    """
    q_lower = question.lower()
    relevant = {"transcript": [], "ocr": [], "scenes": []}

    # Transcript matches
    for seg in ctx.transcript_segments:
        text = seg.get("text", "").lower()
        if any(w in text for w in q_lower.split() if len(w) > 3):
            relevant["transcript"].append({
                "text": seg.get("text"),
                "start": seg.get("start"),
                "end": seg.get("end"),
            })

    # OCR matches
    for ocr in ctx.ocr_results:
        for block in ocr.get("output", {}).get("blocks", []):
            text = block.get("text", "").lower()
            if any(w in text for w in q_lower.split() if len(w) > 3):
                relevant["ocr"].append({
                    "text": block.get("text"),
                    "timestamp": ocr.get("timestamp"),
                    "frame_index": ocr.get("frame_index"),
                })

    # Scene matches
    for scene in ctx.scene_descriptions:
        desc = scene.get("output", {}).get("description", "").lower()
        if any(w in desc for w in q_lower.split() if len(w) > 3):
            relevant["scenes"].append({
                "description": scene.get("output", {}).get("description"),
                "timestamp": scene.get("timestamp"),
                "frame_index": scene.get("frame_index"),
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
        answer_parts.append(f"[Dialogue @ {t['start']:.1f}-{t['end']:.1f}s] {t['text']}")
        timestamps["dialogue"].append({"start": t["start"], "end": t["end"], "text": t["text"]})
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