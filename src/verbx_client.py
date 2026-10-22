import httpx
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

from .config import settings


class VerbXClient:
    """Wrapper for VerbX APIs: STT, OCR, Image Assistant, Translation, TTS."""

    def __init__(self):
        self.api_key = settings.verbx_api_key
        self.base_url = settings.verbx_base_url.rstrip("/")
        if not self.api_key:
            raise ValueError("VERBX_API_KEY not set in .env")
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        self.client = httpx.Client(timeout=120.0)

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        resp = self.client.post(url, headers=self.headers, json=payload)
        resp.raise_for_status()
        return resp.json()

    def _post_file(self, endpoint: str, file_path: str, field_name: str, extra_data: Dict = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        with open(file_path, "rb") as f:
            files = {field_name: (Path(file_path).name, f, "application/octet-stream")}
            data = extra_data or {}
            resp = self.client.post(url, headers={"Authorization": f"Bearer {self.api_key}"}, files=files, data=data)
        resp.raise_for_status()
        return resp.json()

    # --- STT ---
    def stt(self, audio_path: str, language: str = "auto") -> Dict[str, Any]:
        """Speech-to-text with timestamps. Returns segments with start/end/text."""
        return self._post_file("/stt", audio_path, "audio", {"language": language})

    # --- OCR ---
    def ocr(self, image_path: str, language: str = "auto") -> Dict[str, Any]:
        """OCR on a single frame/image. Returns text blocks with bbox + timestamps (frame index)."""
        return self._post_file("/ocr", image_path, "image", {"language": language})

    # --- Image Assistant (Scene Understanding) ---
    def image_assistant(self, image_path: str, prompt: str = "Describe this video frame in detail.") -> Dict[str, Any]:
        """Scene understanding on a frame. Returns description + confidence."""
        return self._post_file("/image-assistant", image_path, "image", {"prompt": prompt})

    # --- Translation ---
    def translate(self, text: str, target_lang: str, source_lang: str = "auto") -> Dict[str, Any]:
        """Translate text to target language."""
        return self._post(
            "/translate",
            {"text": text, "target_language": target_lang, "source_language": source_lang},
        )

    # --- TTS ---
    def tts(self, text: str, language: str, voice: str = "default") -> bytes:
        """Text-to-speech. Returns audio bytes (WAV/MP3)."""
        url = f"{self.base_url}/tts"
        resp = self.client.post(
            url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"text": text, "language": language, "voice": voice},
        )
        resp.raise_for_status()
        return resp.content

    def close(self):
        self.client.close()


# Singleton instance
_verbx_client: Optional[VerbXClient] = None


def get_verbx_client() -> VerbXClient:
    global _verbx_client
    if _verbx_client is None:
        _verbx_client = VerbXClient()
    return _verbx_client