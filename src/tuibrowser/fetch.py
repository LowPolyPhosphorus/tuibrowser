import httpx

HEADERS = {"User-Agent": "tuibrowser/0.1 (+https://github.com/LowPolyPhosphorus/tuibrowser)"}


def fetch(url: str) -> tuple[str, str]:
    """Return (final_url, html). Raises httpx.HTTPError on failure."""
    if "://" not in url:
        url = "https://" + url
    with httpx.Client(follow_redirects=True, timeout=10, headers=HEADERS) as client:
        r = client.get(url)
        r.raise_for_status()
        return str(r.url), r.text