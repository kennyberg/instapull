import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class SavedPost:
    post_id: str
    username: str
    post_url: str
    image_url: str
    video_url: Optional[str]
    caption: str
    hashtags: list[str]
    date: str           # ISO date string, e.g. "2024-01-15"
    post_type: str      # "image", "video", "carousel"
    location: Optional[str]
    ai_description: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    ai_media_type: Optional[str] = None
    ai_frames_analyzed: int = 0


def update_json_index(posts: list[SavedPost], output_dir: Path) -> Path:
    """Append new posts to index.json, skipping any already present."""
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "index.json"

    existing: list[dict] = []
    if index_path.exists():
        existing = json.loads(index_path.read_text(encoding="utf-8"))

    existing_ids = {p["post_id"] for p in existing}
    new_entries = [asdict(p) for p in posts if p.post_id not in existing_ids]
    all_entries = existing + new_entries

    index_path.write_text(
        json.dumps(all_entries, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return index_path
