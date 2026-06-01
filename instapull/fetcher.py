import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Iterator

import instaloader


@dataclass
class RawPost:
    shortcode: str
    username: str
    post_url: str
    image_url: str          # thumbnail for videos, full image for photos
    video_url: Optional[str]
    caption: str
    hashtags: list[str]
    date_utc: datetime
    post_type: str          # "image", "video", "carousel"
    location: Optional[str]


def _extract_hashtags(caption: str) -> list[str]:
    return re.findall(r"#(\w+)", caption or "")


def _post_type(post: instaloader.Post) -> str:
    if post.is_video:
        return "video"
    if post.typename == "GraphSidecar":
        return "carousel"
    return "image"


def _location_name(post: instaloader.Post) -> Optional[str]:
    return None  # Instagram's location API is unreliable; skip to avoid retry loops


def iter_saved_posts(
    loader: instaloader.Instaloader, limit: int = 10
) -> Iterator[RawPost]:
    """Yield up to `limit` saved posts from the authenticated account. 0 = no limit."""
    all_cookies = list(loader.context._session.cookies)
    user_id = next((c.value for c in all_cookies if c.name == "ds_user_id" and c.value), None)
    profile = instaloader.Profile.from_id(loader.context, user_id)
    count = 0
    for post in profile.get_saved_posts():
        yield RawPost(
            shortcode=post.shortcode,
            username=post.owner_username,
            post_url=f"https://www.instagram.com/p/{post.shortcode}/",
            image_url=post.url,
            video_url=post.video_url if post.is_video else None,
            caption=post.caption or "",
            hashtags=_extract_hashtags(post.caption),
            date_utc=post.date_utc,
            post_type=_post_type(post),
            location=_location_name(post),
        )
        count += 1
        if limit and count >= limit:
            break
