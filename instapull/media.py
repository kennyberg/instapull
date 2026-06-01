import io
import math
import os
import tempfile
from pathlib import Path
from typing import Iterable, Optional

from PIL import Image, ImageOps

from .providers.base import MediaFrame

MAX_IMAGE_PX = 1024
DEFAULT_VIDEO_SECONDS_PER_FRAME = 2.0
DEFAULT_VIDEO_MAX_FRAMES = 24
DEFAULT_MAX_VIDEO_MB = 100
VIDEO_FRAME_COUNT_TIERS = [
    (2, 2),
    (5, 3),
    (10, 5),
    (15, 6),
    (20, 8),
    (30, 10),
    (45, 12),
    (60, 14),
    (90, 16),
    (120, 18),
    (180, 20),
    (300, 24),
]

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    )
}


def env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if not value:
        return default
    try:
        parsed = float(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def image_bytes_to_frame(
    image_bytes: bytes, timestamp_seconds: Optional[float] = None
) -> MediaFrame:
    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)
    if max(image.size) > MAX_IMAGE_PX:
        image.thumbnail((MAX_IMAGE_PX, MAX_IMAGE_PX), Image.LANCZOS)

    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=85)
    return MediaFrame(
        data=buf.getvalue(),
        mime_type="image/jpeg",
        timestamp_seconds=timestamp_seconds,
    )


def fetch_image_frame(image_url: str) -> MediaFrame:
    import requests

    response = requests.get(image_url, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()
    return image_bytes_to_frame(response.content)


def choose_video_frame_count(
    duration_seconds: Optional[float],
    *,
    seconds_per_frame: float = DEFAULT_VIDEO_SECONDS_PER_FRAME,
    max_frames: int = DEFAULT_VIDEO_MAX_FRAMES,
) -> int:
    if not duration_seconds or duration_seconds <= 0:
        return min(5, max_frames)

    for max_duration, frame_count in VIDEO_FRAME_COUNT_TIERS:
        if duration_seconds <= max_duration:
            return min(frame_count, max_frames)

    count = math.ceil(duration_seconds / seconds_per_frame)
    return max(1, min(max_frames, count))


def frame_timestamps(duration_seconds: float, frame_count: int) -> list[float]:
    if frame_count <= 1:
        return [max(0.0, duration_seconds / 2)]

    segment_seconds = duration_seconds / frame_count
    timestamps = [
        (segment_seconds * index) + (segment_seconds / 2)
        for index in range(frame_count)
    ]
    return [
        min(max(0.0, value), max(0.0, duration_seconds - 0.05))
        for value in timestamps
    ]


def download_video_to_temp(video_url: str, max_mb: int = DEFAULT_MAX_VIDEO_MB) -> Path:
    import requests

    max_bytes = max_mb * 1024 * 1024
    response = requests.get(
        video_url,
        headers=REQUEST_HEADERS,
        stream=True,
        timeout=(10, 60),
    )
    response.raise_for_status()

    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            expected_size = int(content_length)
        except ValueError:
            expected_size = 0
        if expected_size > max_bytes:
            raise RuntimeError(
                f"Video is larger than the configured limit of {max_mb} MB."
            )

    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    path = Path(handle.name)
    written = 0
    try:
        with handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                written += len(chunk)
                if written > max_bytes:
                    raise RuntimeError(
                        f"Video is larger than the configured limit of {max_mb} MB."
                    )
                handle.write(chunk)
    except Exception:
        path.unlink(missing_ok=True)
        raise

    return path


def sample_video_frames(video_url: str) -> list[MediaFrame]:
    seconds_per_frame = env_float(
        "INSTAPULL_VIDEO_SECONDS_PER_FRAME", DEFAULT_VIDEO_SECONDS_PER_FRAME
    )
    max_frames = env_int("INSTAPULL_VIDEO_MAX_FRAMES", DEFAULT_VIDEO_MAX_FRAMES)
    max_video_mb = env_int("INSTAPULL_MAX_VIDEO_MB", DEFAULT_MAX_VIDEO_MB)

    video_path = download_video_to_temp(video_url, max_mb=max_video_mb)
    try:
        return sample_video_file(
            video_path,
            seconds_per_frame=seconds_per_frame,
            max_frames=max_frames,
        )
    finally:
        video_path.unlink(missing_ok=True)


def sample_video_file(
    video_path: Path,
    *,
    seconds_per_frame: float = DEFAULT_VIDEO_SECONDS_PER_FRAME,
    max_frames: int = DEFAULT_VIDEO_MAX_FRAMES,
) -> list[MediaFrame]:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "opencv-python-headless is not installed. Run: pip install opencv-python-headless"
        ) from exc

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError("Could not open the video file for frame extraction.")

    try:
        fps = capture.get(cv2.CAP_PROP_FPS) or 0
        total_frames = capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        duration_seconds = total_frames / fps if fps > 0 and total_frames > 0 else None
        frame_count = choose_video_frame_count(
            duration_seconds,
            seconds_per_frame=seconds_per_frame,
            max_frames=max_frames,
        )

        if duration_seconds:
            timestamps = frame_timestamps(duration_seconds, frame_count)
        else:
            timestamps = []

        frames = _read_timestamped_frames(capture, timestamps)
        if not frames and total_frames > 0:
            frames = _read_indexed_frames(capture, total_frames, frame_count)
    finally:
        capture.release()

    if not frames:
        raise RuntimeError("Could not extract any frames from the video.")

    return frames


def _read_timestamped_frames(capture, timestamps: Iterable[float]) -> list[MediaFrame]:
    import cv2

    frames = []
    for timestamp in timestamps:
        capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ok, raw_frame = capture.read()
        if ok:
            frames.append(_cv_frame_to_media_frame(raw_frame, timestamp))
    return frames


def _read_indexed_frames(
    capture, total_frames: float, frame_count: int
) -> list[MediaFrame]:
    import cv2

    frames = []
    for index in range(frame_count):
        target = int(((index + 0.5) / frame_count) * total_frames)
        capture.set(cv2.CAP_PROP_POS_FRAMES, target)
        ok, raw_frame = capture.read()
        if ok:
            frames.append(_cv_frame_to_media_frame(raw_frame, None))
    return frames


def _cv_frame_to_media_frame(raw_frame, timestamp_seconds: Optional[float]) -> MediaFrame:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "opencv-python-headless is not installed. Run: pip install opencv-python-headless"
        ) from exc

    rgb_frame = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb_frame)
    buf = io.BytesIO()
    if max(image.size) > MAX_IMAGE_PX:
        image.thumbnail((MAX_IMAGE_PX, MAX_IMAGE_PX), Image.LANCZOS)
    image.convert("RGB").save(buf, format="JPEG", quality=85)
    return MediaFrame(
        data=buf.getvalue(),
        mime_type="image/jpeg",
        timestamp_seconds=timestamp_seconds,
    )
