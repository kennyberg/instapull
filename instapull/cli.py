import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from .providers import PROVIDER_NAMES

load_dotenv()

DEFAULT_OUTPUT = Path(
    os.environ.get("INSTAPULL_OUTPUT_DIR", Path.home() / "instapull-data")
)
DEFAULT_PROVIDER = os.environ.get("INSTAPULL_PROVIDER", "none").lower()
if DEFAULT_PROVIDER not in PROVIDER_NAMES + ["none"]:
    DEFAULT_PROVIDER = "none"


@click.group()
def main():
    """InstaPull - turn Instagram saves into AI-agent-readable memory."""
    pass


@main.command()
@click.option(
    "--limit",
    default=10,
    show_default=True,
    help="How many saved posts to fetch. Use 0 for all.",
)
@click.option(
    "--browser",
    default="chrome",
    show_default=True,
    type=click.Choice(["chrome", "firefox", "chromium", "edge"]),
    help="Which browser to read your Instagram session from.",
)
@click.option(
    "--output",
    default=str(DEFAULT_OUTPUT),
    show_default=True,
    help="Folder where index.json will be saved.",
)
@click.option(
    "--provider",
    default=DEFAULT_PROVIDER,
    show_default=True,
    type=click.Choice(PROVIDER_NAMES + ["none"]),
    help="Vision AI provider for image and video analysis. Use 'none' to skip.",
)
def sync(
    limit: int,
    browser: str,
    output: str,
    provider: str,
):
    """Fetch your Instagram saved posts and save them to index.json."""

    import instaloader

    from .auth import create_loader
    from .fetcher import iter_saved_posts
    from .media import fetch_image_frame, sample_video_frames
    from .providers import get_provider
    from .providers.base import AnalysisContext
    from .storage import SavedPost, update_json_index

    vision = None
    if provider != "none":
        try:
            vision = get_provider(provider)
        except RuntimeError as e:
            click.echo(f"Error loading vision provider: {e}", err=True)
            sys.exit(1)

    output_dir = Path(output)

    # Connect to Instagram.
    click.echo(f"Reading Instagram session from {browser}...")
    try:
        loader = create_loader(browser)
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    limit_label = str(limit) if limit else "all"
    click.echo(f"Fetching {limit_label} saved posts...\n")

    collected: list[SavedPost] = []

    try:
        for i, raw in enumerate(iter_saved_posts(loader, limit=limit), 1):
            click.echo(f"  [{i:>2}] @{raw.username}  ({raw.post_type})  {raw.post_url}")

            ai_desc = None
            ai_frames_analyzed = 0
            ai_media_type = None
            if vision:
                try:
                    context = AnalysisContext(
                        post_type=raw.post_type,
                        post_url=raw.post_url,
                        caption=raw.caption,
                    )
                    if raw.post_type == "video" and raw.video_url:
                        frames = sample_video_frames(raw.video_url)
                        ai_desc = vision.describe_video(frames, context)
                        ai_frames_analyzed = len(frames)
                        ai_media_type = "video"
                        click.echo(
                            f"       AI video: analyzed {len(frames)} frame(s)"
                        )
                    else:
                        image = fetch_image_frame(raw.image_url)
                        ai_desc = vision.describe_image(image, context)
                        ai_frames_analyzed = 1
                        ai_media_type = "image"
                        click.echo("       AI image: analyzed 1 image")
                    click.echo(f"       AI: {_preview(ai_desc)}")
                except Exception as e:
                    click.echo(f"       AI description skipped: {e}")

            post = SavedPost(
                post_id=raw.shortcode,
                username=raw.username,
                post_url=raw.post_url,
                image_url=raw.image_url,
                video_url=raw.video_url,
                caption=raw.caption,
                hashtags=raw.hashtags,
                date=raw.date_utc.strftime("%Y-%m-%d"),
                post_type=raw.post_type,
                location=raw.location,
                ai_description=ai_desc,
                ai_provider=vision.name if vision and ai_desc else None,
                ai_model=vision.model if vision and ai_desc else None,
                ai_media_type=ai_media_type,
                ai_frames_analyzed=ai_frames_analyzed,
            )

            click.echo("       Added to index\n")
            collected.append(post)

    except instaloader.exceptions.LoginRequiredException:
        click.echo(
            "\nInstagram says you are not logged in.\n"
            "Make sure you are logged into Instagram in your browser and try again.",
            err=True,
        )
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\nStopped early.")

    # Summary.
    if collected:
        index_path = update_json_index(collected, output_dir)
        click.echo(f"Done! {len(collected)} post(s) saved to {output_dir}/")
        click.echo(f"JSON index updated: {index_path}")
    else:
        click.echo("No posts were saved.")


def _preview(text: str, max_len: int = 90) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_len:
        return normalized
    return f"{normalized[:max_len]}..."


if __name__ == "__main__":
    main()
