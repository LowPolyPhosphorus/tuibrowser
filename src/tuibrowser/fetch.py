import html as _html

import httpx

HEADERS = {"User-Agent": "tuibrowser/0.1"}

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

def fetch_js(url: str) -> tuple[str, str]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError("JS mode needs: pip install playwright, then: playwright install chromium")
    if "://" not in url:
        url = "https://" + url
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url, wait_until="load", timeout=20000)
            page.wait_for_timeout(1500)
            return page.url, page.content()
        finally:
            browser.close()