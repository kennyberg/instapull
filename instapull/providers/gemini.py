import os
import time
from typing import Sequence

from .base import (
    AnalysisContext,
    IMAGE_PROMPT,
    VIDEO_PROMPT,
    MediaFrame,
    VisionProvider,
)

DEFAULT_MODEL = "gemini-2.5-flash-lite"


class GeminiProvider(VisionProvider):
    """
    Google Gemini vision provider.
    Supports either the Gemini Developer API or Vertex AI.
    """

    name = "gemini"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: str = "",
        use_vertex: bool = False,
        project: str = "",
        location: str = "",
    ):
        try:
            from google import genai
        except ImportError:
            raise RuntimeError(
                "google-genai is not installed. Run: pip install google-genai"
            )
        if use_vertex:
            self._client = genai.Client(
                vertexai=True,
                project=project or None,
                location=location or None,
            )
        else:
            if not api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is not set. Add it to your .env file."
                )
            self._client = genai.Client(api_key=api_key)
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    @classmethod
    def from_env(cls) -> "GeminiProvider":
        model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
        use_vertex = (
            os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower()
            in {"1", "true", "yes"}
            or os.environ.get("GOOGLE_GENAI_USE_ENTERPRISE", "").lower()
            in {"1", "true", "yes"}
        )

        if use_vertex:
            project = (
                os.environ.get("GOOGLE_CLOUD_PROJECT")
                or os.environ.get("GOOGLE_PROJECT_ID")
                or ""
            )
            location = (
                os.environ.get("GOOGLE_CLOUD_LOCATION")
                or os.environ.get("GOOGLE_LOCATION")
                or "us-central1"
            )
            if not project:
                raise RuntimeError(
                    "GOOGLE_GENAI_USE_VERTEXAI is true, but GOOGLE_CLOUD_PROJECT "
                    "is not set. Add GOOGLE_CLOUD_PROJECT to your .env file or "
                    "turn off Vertex AI mode."
                )
            return cls(
                model=model,
                use_vertex=True,
                project=project,
                location=location,
            )

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        return cls(api_key=api_key or "", model=model)

    def describe_image(self, image: MediaFrame, context: AnalysisContext) -> str:
        from google.genai import types

        contents = [
            types.Part.from_bytes(data=image.data, mime_type=image.mime_type),
            self._context_prompt(IMAGE_PROMPT, context),
        ]
        return self._generate_content(contents)

    def describe_video(
        self, frames: Sequence[MediaFrame], context: AnalysisContext
    ) -> str:
        from google.genai import types

        contents = [self._context_prompt(VIDEO_PROMPT, context)]
        for index, frame in enumerate(frames, 1):
            label = _frame_label(index, frame)
            contents.append(label)
            contents.append(
                types.Part.from_bytes(data=frame.data, mime_type=frame.mime_type)
            )
        return self._generate_content(contents)

    def _generate_content(self, contents) -> str:
        for attempt in range(3):
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=contents,
                )
                return response.text.strip()
            except Exception as e:
                retryable = (
                    "503" in str(e)
                    or "429" in str(e)
                    or "UNAVAILABLE" in str(e)
                    or "EXHAUSTED" in str(e)
                )
                if attempt < 2 and retryable:
                    time.sleep(10 * (attempt + 1))
                else:
                    raise

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


def _frame_label(index: int, frame: MediaFrame) -> str:
    if frame.timestamp_seconds is None:
        return f"Frame {index}"
    return f"Frame {index} at {frame.timestamp_seconds:.1f} seconds"
