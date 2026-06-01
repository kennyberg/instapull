from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import instaloader

BrowserType = Literal["chrome", "firefox", "chromium", "edge"]


def _make_loader() -> "instaloader.Instaloader":
    import instaloader

    return instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
        max_connection_attempts=3,
    )


def _authenticate(L: "instaloader.Instaloader") -> "instaloader.Instaloader":
    """Resolve the logged-in user from cookies and set it on the loader context."""
    import instaloader

    all_cookies = list(L.context._session.cookies)
    user_id = next(
        (c.value for c in all_cookies if c.name == "ds_user_id" and c.value),
        None,
    )
    if not user_id:
        raise RuntimeError(
            "Could not find your Instagram user ID in the browser cookies. "
            "Make sure you are logged into Instagram in your browser."
        )
    profile = instaloader.Profile.from_id(L.context, user_id)
    L.context.username = profile.username
    return L


def create_loader(browser: BrowserType = "chrome") -> "instaloader.Instaloader":
    """Authenticate by reading cookies from an installed browser."""
    import browser_cookie3

    L = _make_loader()

    cookie_fn = {
        "chrome": browser_cookie3.chrome,
        "firefox": browser_cookie3.firefox,
        "chromium": browser_cookie3.chromium,
        "edge": browser_cookie3.edge,
    }[browser]

    try:
        cookies = cookie_fn(domain_name=".instagram.com")
        L.context._session.cookies.update(cookies)
    except Exception as e:
        raise RuntimeError(
            f"Could not read cookies from {browser}. "
            f"Make sure you are logged into Instagram in that browser.\n"
            f"Original error: {e}"
        )

    return _authenticate(L)

