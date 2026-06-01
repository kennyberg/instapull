import base64
import os
from typing import Sequence

from .base import (
    AnalysisContext,
    IMAGE_PROMPT,
    VIDEO_PROMPT,
    MediaFrame,
    VisionProvider,
)

DEFAULT_MODEL = "qwen2.5vl"
DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_TIMEOUT_SECONDS = 120


class OllamaProvider(VisionProvider):
    """Local vision provider that talks to an Ollama server on this machine."""

    name = "ollama"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        session=None,
    ):
        if session is None:
            import requests

            session = requests.Session()
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._session = session

    @property
    def model(self) -> str:
        return self._model

    @classmethod
    def from_env(cls) -> "OllamaProvider":
        model = os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)
        base_url = os.environ.get("OLLAMA_HOST", DEFAULT_BASE_URL)
        timeout_seconds = _env_int("OLLAMA_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
        return cls(
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )

    def describe_image(self, image: MediaFrame, context: AnalysisContext) -> str:
        return self._generate(
            prompt=self._context_prompt(IMAGE_PROMPT, context),
            frames=[image],
        )

    def describe_video(
        self, frames: Sequence[MediaFrame], context: AnalysisContext
    ) -> str:
        labels = "\n".join(_frame_label(index, frame) for index, frame in enumerate(frames, 1))
        prompt = (
            f"{self._context_prompt(VIDEO_PROMPT, context)}\n\n"
            "The attached frames are provided in this order:\n"
            f"{labels}"
        )
        return self._generate(prompt=prompt, frames=frames)

    def _generate(self, prompt: str, frames: Sequence[MediaFrame]) -> str:
        import requests

        payload = {
            "model": self._model,
            "prompt": prompt,
            "images": [_base64_image(frame) for frame in frames],
            "stream": False,
        }

        try:
            response = self._session.post(
                f"{self._base_url}/api/generate",
                json=payload,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except requests.ConnectionError as exc:
            raise RuntimeError(
                "Could not connect to Ollama. Make sure Ollama is running, then try again."
            ) from exc
        except requests.HTTPError as exc:
            raise RuntimeError(
                "Ollama returned an error. Make sure the selected model is installed "
                f"and supports vision: ollama pull {self._model}"
            ) from exc

        data = response.json()
        text = (data.get("response") or "").strip()
        if not text:
            raise RuntimeError("Ollama returned an empty response.")
        return text

    def _context_prompt(self, prompt: str, context: AnalysisContext) -> str:
        caption = context.caption.strip()
        if not caption:
            return prompt
        return (
            f"{prompt}\n\n"
            "The Instagram caption is included as context. "
            "Use it only when it helps explain the visual content.\n"
            f"Caption: {caption}"
        )


def _base64_image(frame: MediaFrame) -> str:
    return base64.b64encode(frame.data).decode("ascii")


def _frame_label(index: int, frame: MediaFrame) -> str:
    if frame.timestamp_seconds is None:
        return f"Frame {index}"
    return f"Frame {index} at {frame.timestamp_seconds:.1f} seconds"


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default
