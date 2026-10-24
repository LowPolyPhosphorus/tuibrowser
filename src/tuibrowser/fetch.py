import html as _html
import httpx

from concurrent.futures import ThreadPoolExecutor
from .layout import CELL_W

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

_pw_pool = ThreadPoolExecutor(max_workers=1)
_pw: dict = {}
_SKIP_TYPES = ("image", "media", "font", "stylesheet")


def _pw_fetch(url: str) -> tuple[str, str]:
    if "browser" not in _pw:
        from playwright.sync_api import sync_playwright
        _pw["pw"] = sync_playwright().start()
        _pw["browser"] = _pw["pw"].chromium.launch()
    page = _pw["browser"].new_page()
    try:
        page.route(
            "**/*",
            lambda r: r.abort() if r.request.resource_type in _SKIP_TYPES else r.continue_(),
        )
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        try:
            page.wait_for_load_state("networkidle", timeout=2500)
        except Exception:
            pass
        return page.url, page.content()
    finally:
        page.close()


def fetch_js(url: str) -> tuple[str, str]:
    try:
        import playwright # noqa: F401
    except ImportError:
        raise RuntimeError("JS mode needs: pip install playwright, then: playwright install chromium")
    if "://" not in url:
        url = "https://" + url
    return _pw_pool.submit(_pw_fetch, url).result()


def close_js() -> None:
    if _pw:
        _pw_pool.submit(lambda: (_pw["browser"].close(), _pw["pw"].stop())).result()


_LAYOUT_JS = r"""
() => {
  const out = [], ids = new Map();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const range = document.createRange();
  let n, count = 0;
  while ((n = walker.nextNode()) && count < 6000) {
    const el = n.parentElement;
    if (!el || ['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE'].includes(el.tagName)) continue;
    const text = n.textContent;
    if (!text.trim()) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || cs.opacity === '0') continue;
    const a = el.closest('a[href]');
    let href = null, aid = null;
    if (a && /^https?:/i.test(a.href) && !(a.getAttribute('href') || '').startsWith('#')) {
      href = a.href;
      if (!ids.has(a)) ids.set(a, ids.size);
      aid = ids.get(a);
    }
    const bold = parseInt(cs.fontWeight) >= 600;
    const re = /\S+/g;
    let m, line = null;
    while ((m = re.exec(text))) {
      range.setStart(n, m.index);
      range.setEnd(n, m.index + m[0].length);
      const r = range.getClientRects()[0];
      if (!r || r.width === 0 || r.right <= 0) continue;
      const x = Math.round(r.left + scrollX), y = Math.round(r.top + scrollY);
      if (line && Math.abs(line.y - y) < 6) {
        line.text += ' ' + m[0];
      } else {
        line = {x: x, y: y, text: m[0], href: href, aid: aid, b: bold};
        out.push(line);
      }
      count++;
    }
  }
  return out;
}
"""


def _pw_layout(url: str, cols: int):
    if "browser" not in _pw:
        from playwright.sync_api import sync_playwright
        _pw["pw"] = sync_playwright().start()
        _pw["browser"] = _pw["pw"].chromium.launch()
    page = _pw["browser"].new_page(viewport={"width": max(cols * CELL_W, 400), "height": 900})
    try:
        page.route(
            "**/*",
            lambda r: r.abort() if r.request.resource_type in ("image", "media", "font") else r.continue_(),
        )
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        try:
            page.wait_for_load_state("networkidle", timeout=2500)
        except Exception:
            pass
        return page.url, page.evaluate(_LAYOUT_JS), page.content()
    finally:
        page.close()


def fetch_layout(url: str, cols: int):
    try:
        import playwright # noqa: F401
    except ImportError:
        raise RuntimeError("Layout mode needs: pip install playwright, then: playwright install chromium")
    if "://" not in url:
        url = "https://" + url
    return _pw_pool.submit(_pw_layout, url, cols).result()