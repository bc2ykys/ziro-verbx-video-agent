import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
import ffmpeg


def has_audio_stream(video_path: str) -> bool:
    """Check if video has an audio stream."""
    probe = ffmpeg.probe(video_path)
    return any(s.get("codec_type") == "audio" for s in probe.get("streams", []))


def extract_audio(video_path: str, output_audio: str, sample_rate: int = 16000) -> str:
    """Extract mono audio at 16kHz for STT. Creates silent audio if no audio stream."""
    if has_audio_stream(video_path):
        (
            ffmpeg.input(video_path)
            .output(output_audio, ac=1, ar=sample_rate, format="wav")
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    else:
        # Create silent audio track (5s minimum) so STT doesn't crash
        duration = get_video_duration(video_path)
        (
            ffmpeg.input(f"anullsrc=r={sample_rate}:cl=mono", f="lavfi", t=duration)
            .output(output_audio, ac=1, ar=sample_rate, format="wav")
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    return output_audio


def extract_frames(video_path: str, output_dir: str, fps: float = 1.0) -> List[str]:
    """Extract frames at given fps (default 1 fps). Returns list of frame paths."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    pattern = str(Path(output_dir) / "frame_%04d.jpg")
    (
        ffmpeg.input(video_path)
        .output(pattern, vf=f"fps={fps}", format="image2", vcodec="mjpeg")
        .overwrite_output()
        .run(capture_stdout=True, capture_stderr=True)
    )
    frames = sorted(Path(output_dir).glob("frame_*.jpg"))
    return [str(f) for f in frames]


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds."""
    probe = ffmpeg.probe(video_path)
    return float(probe["format"]["duration"])


def get_video_info(video_path: str) -> Dict[str, Any]:
    """Get video metadata."""
    probe = ffmpeg.probe(video_path)
    video_stream = next((s for s in probe["streams"] if s["codec_type"] == "video"), {})
    audio_stream = next((s for s in probe["streams"] if s["codec_type"] == "audio"), {})
    return {
        "duration": float(probe["format"]["duration"]),
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "fps": eval(video_stream.get("r_frame_rate", "0/1")) if video_stream.get("r_frame_rate") else 0,
        "has_audio": bool(audio_stream),
    }


def frame_index_to_timestamp(frame_idx: int, fps: float) -> float:
    """Convert frame index (0-based) to timestamp in seconds."""
    return frame_idx / fps


def timestamp_to_frame_idx(timestamp: float, fps: float) -> int:
    """Convert timestamp to nearest frame index."""
    return int(round(timestamp * fps))