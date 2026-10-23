import httpx
import base64
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

from .config import settings


class VerbXClient:
    """Wrapper for VerbX SaaS Playground APIs: STT, OCR, Translation, TTS."""

    def __init__(self):
        self.access_token = getattr(settings, 'verbx_access_token', None) or settings.verbx_api_key
        self.base_url = "https://api.verbxeco.com"
        if not self.access_token:
            raise ValueError("VERBX_ACCESS_TOKEN not set in .env (run login first)")
        self.headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}
        self.client = httpx.Client(timeout=120.0)
        self.max_retries = 3
        self.retry_delay = 2

    def _post_saas(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Post to saas/playground endpoint with tenant_context and retry logic."""
        url = f"{self.base_url}{endpoint}"
        if "tenant_context" not in payload:
            payload["tenant_context"] = {}
        
        for attempt in range(self.max_retries):
            try:
                resp = self.client.post(url, headers=self.headers, json=payload)
                if resp.status_code in (502, 503) and attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                resp.raise_for_status()
                return resp.json()
            except (httpx.ReadError, httpx.ConnectError) as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise
        
        # Final attempt
        resp = self.client.post(url, headers=self.headers, json=payload)
        resp.raise_for_status()
        return resp.json()

    def _post_saas_file_b64(self, endpoint: str, file_b64: str, field_name: str, extra_data: Dict = None) -> Dict[str, Any]:
        """Post base64 file to saas/playground endpoint."""
        payload = {field_name: file_b64, "tenant_context": {}}
        if extra_data:
            payload.update(extra_data)
        return self._post_saas(endpoint, payload)

    # --- STT (SaaS Playground) ---
    def stt(self, audio_path: str, language: str = "en") -> Dict[str, Any]:
        """Speech-to-text with timestamps via SaaS playground."""
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        
        max_size = 800 * 1024
        if len(audio_data) > max_size:
            import ffmpeg, tempfile, os
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                short_audio = tmp.name
            try:
                (
                    ffmpeg.input(audio_path)
                    .output(short_audio, ac=1, ar=16000, format='wav', t=10)
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                with open(short_audio, 'rb') as f:
                    audio_data = f.read()
            finally:
                if os.path.exists(short_audio):
                    os.unlink(short_audio)
        
        audio_b64 = base64.b64encode(audio_data).decode()

        payload = {
            "audio_base64": audio_b64,
            "language": language,
            "enable_timestamps": True,
            "enable_word_timestamps": False,
            "tenant_context": {}
        }
        try:
            result = self._post_saas("/saas/playground/stt", payload)
            return result
        except (httpx.HTTPStatusError, httpx.ReadError, httpx.ConnectError) as e:
            status = getattr(e.response, 'status_code', 0) if hasattr(e, 'response') else 0
            if status in (401, 413, 422, 502) or "stt_refused" in str(e) or isinstance(e, httpx.ConnectError):
                return {"segments": []}
            raise

    # --- OCR (SaaS Playground) ---
    def ocr(self, image_path: str, language: str = "en") -> Dict[str, Any]:
        """OCR on a single frame/image via SaaS playground."""
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        payload = {
            "image_base64": img_b64,
            "source_lang": language if language != "auto" else "en",
            "target_lang": language if language != "auto" else "en",
            "tenant_context": {}
        }
        try:
            result = self._post_saas("/saas/playground/ocr", payload)
            return {
                "output": {
                    "blocks": [
                        {
                            "text": result.get("extracted_text", ""),
                            "translated": result.get("translated_text", ""),
                            "box": b.get("box", []),
                            "confidence": b.get("confidence", 0.0),
                        }
                        for b in result.get("blocks", [])
                    ]
                }
            }
        except (httpx.HTTPStatusError, httpx.ReadError, httpx.ConnectError) as e:
            status = getattr(e.response, 'status_code', 0) if hasattr(e, 'response') else 0
            if status in (401, 413, 422, 502) or isinstance(e, httpx.ConnectError):
                return {"output": {"blocks": [{"text": "OCR unavailable (API error)", "translated": "", "box": [], "confidence": 0.0}]}}
            raise

    # --- Image Assistant (SaaS Playground - use assist endpoint) ---
    def image_assistant(self, image_path: str, prompt: str = "Describe this video frame in detail.") -> Dict[str, Any]:
        """Scene understanding on a frame via SaaS assist endpoint."""
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        payload = {
            "prompt": prompt,
            "images": [img_b64],
            "language": "en",
            "tenant_context": {}
        }
        try:
            result = self._post_saas("/v1/assist", payload)
            desc = ""
            if isinstance(result, dict):
                desc = result.get("response") or result.get("text") or str(result)
            return {"output": {"description": desc}}
        except Exception:
            return {"output": {"description": "Frame processed (scene understanding unavailable on current plan)"}}

    # --- Translation (SaaS Playground) ---
    def translate(self, text: str, target_lang: str, source_lang: str = "auto") -> Dict[str, Any]:
        """Translate text to target language via SaaS playground."""
        payload = {
            "text": text,
            "source_lang": source_lang if source_lang != "auto" else "en",
            "target_lang": target_lang,
            "tenant_context": {}
        }
        try:
            result = self._post_saas("/saas/playground/translate", payload)
            return {
                "translated_text": result.get("translated_text", text),
                "source_lang": result.get("source_lang", source_lang),
                "target_lang": result.get("target_lang", target_lang),
            }
        except (httpx.HTTPStatusError, httpx.ReadError, httpx.ConnectError) as e:
            status = getattr(e.response, 'status_code', 0) if hasattr(e, 'response') else 0
            if status in (401, 413, 422, 502) or isinstance(e, httpx.ConnectError):
                return {"translated_text": text, "source_lang": source_lang, "target_lang": target_lang}
            raise

    # --- TTS (SaaS Playground) ---
    def tts(self, text: str, language: str, voice: str = "default") -> bytes:
        """Text-to-speech via SaaS playground. Returns audio bytes."""
        payload = {
            "text": text,
            "language": language,
            "tenant_context": {}
        }
        try:
            result = self._post_saas("/saas/playground/tts", payload)
            audio_b64 = result.get("audio_b64", "")
            if audio_b64:
                return base64.b64decode(audio_b64)
            return b""
        except (httpx.HTTPStatusError, httpx.ReadError, httpx.ConnectError) as e:
            status = getattr(e.response, 'status_code', 0) if hasattr(e, 'response') else 0
            if status in (401, 413, 422, 502) or isinstance(e, httpx.ConnectError):
                return b""
            raise

    def close(self):
        self.client.close()


# Singleton instance
_verbx_client: Optional[VerbXClient] = None


def get_verbx_client() -> VerbXClient:
    global _verbx_client
    if _verbx_client is None:
        _verbx_client = VerbXClient()
    return _verbx_client