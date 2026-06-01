from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Sequence


IMAGE_PROMPT = (
    "Describe this Instagram image in 2-3 sentences. "
    "Focus on the main subject, visual style, mood, visible text, and notable details. "
    "Be specific and concise. This description will be stored as a searchable memory entry."
)


VIDEO_PROMPT = (
    "You are analyzing sampled frames from an Instagram video. "
    "The frames are in chronological order. Write a video analysis, not separate image captions. "
    "Explain what appears to happen across the clip, mention important people, objects, setting, "
    "visual style, mood, and any visible text. If the exact motion is uncertain from the sampled "
    "frames, say so briefly instead of inventing details. Format the answer with these labels: "
    "Summary, Sequence, Visual details, Visible text, Search keywords."
)


@dataclass
class MediaFrame:
    """A JPEG frame prepared for an AI vision provider."""

    data: bytes
    mime_type: str = "image/jpeg"
    timestamp_seconds: Optional[float] = None


@dataclass
class AnalysisContext:
    """Useful post details that can improve the AI description."""

    post_type: str
    post_url: str
    caption: str = ""


class VisionProvider(ABC):
    """Any vision provider must implement image and video analysis."""

    name: str

    @property
    @abstractmethod
    def model(self) -> str:
        """Return the configured model name."""
        raise NotImplementedError

    @abstractmethod
    def describe_image(self, image: MediaFrame, context: AnalysisContext) -> str:
        """Return a short text description for one image."""
        raise NotImplementedError

    @abstractmethod
    def describe_video(
        self, frames: Sequence[MediaFrame], context: AnalysisContext
    ) -> str:
        """Return a video-specific description from sampled frames."""
        raise NotImplementedError
