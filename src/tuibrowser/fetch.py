import html as _html

import httpx

HEADERS = {"User-Agent": "..."}   # keep your existing line

_client = httpx.Client(follow_redirects=True, timeout=10, headers=HEADERS)


def fetch(url: str, data: dict | None = None) -> tuple[str, str]:
    """Return (final_url, html). Raises httpx.HTTPError on failure."""
    if "://" not in url:
        url = "https://" + url
    r = _client.post(url, data=data) if data is not None else _client.get(url)
    r.raise_for_status()
    ctype = r.headers.get("content-type", "").lower()
    if "text/plain" in ctype:
        return str(r.url), f"<pre>{_html.escape(r.text)}</pre>"
    if ctype and not any(t in ctype for t in ("html", "xml", "text/")):
        msg = f"{_html.escape(ctype)}, {len(r.content)} bytes"
        return str(r.url), f"<h1>Not a web page</h1><p>{msg}</p>"
    return str(r.url), r.text