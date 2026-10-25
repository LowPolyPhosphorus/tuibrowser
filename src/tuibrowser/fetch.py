import html as _html
import httpx

from concurrent.futures import ThreadPoolExecutor
from .layout import CELL_W

HEADERS = {"User-Agent": "tuibrowser/0.1 (+https://github.com/LowPolyPhosphorus/tuibrowser; terminal browser) httpx"}

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

def _run_pw(fn, *args):
    global _pw_pool
    try:
        return _pw_pool.submit(fn, *args).result(timeout=45)
    except Exception:
        _pw.clear()
        _pw_pool = ThreadPoolExecutor(max_workers=1)
        raise

def fetch_js(url: str) -> tuple[str, str]:
    try:
        import playwright # noqa: F401
    except ImportError:
        raise RuntimeError("JS mode needs: pip install playwright, then: playwright install chromium")
    if "://" not in url:
        url = "https://" + url
    return _run_pw(_pw_fetch, url)


def close_js() -> None:
    if _pw:
        _pw_pool.submit(lambda: (_pw["browser"].close(), _pw["pw"].stop())).result()


_LAYOUT_JS = r"""
() => {
  const out = [], ids = new Map(), wanted = new Set(), hiddenCache = new Map();
  const isHidden = (e) => {
    if (!e || e === document.body) return false;
    if (hiddenCache.has(e)) return hiddenCache.get(e);
    const s = getComputedStyle(e);
    let hide = s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0';
    if (!hide) {
      const r = e.getBoundingClientRect();
      const clipped = s.overflowX !== 'visible' || s.overflowY !== 'visible' || s.clip !== 'auto' || s.clipPath !== 'none';
      hide = (r.width <= 2 || r.height <= 2) && clipped;
    }
    if (!hide) hide = isHidden(e.parentElement);
    hiddenCache.set(e, hide);
    return hide;
  };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const range = document.createRange();
  let n, count = 0;
  while ((n = walker.nextNode()) && count < 6000) {
    const el = n.parentElement;
    if (!el || ['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE'].includes(el.tagName)) continue;
    const text = n.textContent;
    if (!text.trim()) continue;
    if (isHidden(el)) continue;
    const cs = getComputedStyle(el);
    const a = el.closest('a[href]');
    let href = null, aid = null;
    const raw = a ? (a.getAttribute('href') || '') : '';
    if (a && /^https?:/i.test(a.href) && raw !== '#') {
      if (raw.startsWith('#')) {
        try { wanted.add(decodeURIComponent(raw.slice(1))); } catch (e) {}
      }
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
  for (const id of wanted) {
    const t = document.getElementById(id);
    if (!t) continue;
    const r = t.getBoundingClientRect();
    out.push({x: 0, y: Math.round(r.top + scrollY), text: '', anchor: id, aid: null, href: null, b: false});
  }
  let k = 0;
  for (const im of document.images) {
    if (k >= 40) break;
    const r = im.getBoundingClientRect();
    if (r.width < 32 || r.height < 32) continue;
    const cs = getComputedStyle(im);
    if (cs.visibility === 'hidden' || cs.display === 'none' || cs.opacity === '0') continue;
    let src = im.currentSrc || im.getAttribute('data-src') || im.src || '';
    if (!src || src.startsWith('data:') || /\.svg(\?|$)/i.test(src)) continue;
    try { src = new URL(src, document.baseURI).href; } catch (e) { continue; }
    out.push({x: Math.round(r.left + scrollX), y: Math.round(r.top + scrollY), text: '[img]', img: src, aid: null, href: null, b: true});
    k++;
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
    return _run_pw(_pw_layout, url, cols)

def fetch_image(url: str) -> bytes:
    r = _client.get(url)
    r.raise_for_status()
    if len(r.content) > 3_000_000:
        raise ValueError("image too large")
    return r.content