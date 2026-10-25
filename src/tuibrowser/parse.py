from urllib.parse import parse_qs, urlparse, urljoin

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

SKIP = {"script", "style", "noscript", "head", "svg", "template"}
BLOCKS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre"]

def _unwrap(url: str) -> str:
    u = urlparse(url)
    if u.netloc.endswith("duckduckgo.com") and u.path.startswith("/l/"):
        target = parse_qs(u.query).get("uddg")
        if target:
            return target[0]
    return url


def _inline(node, base, links, flat=False):
    out = []
    for child in node.children:
        if isinstance(child, Comment):
            continue
        if isinstance(child, NavigableString):
            out.append(str(child))
        elif isinstance(child, Tag) and child.name not in SKIP and (flat or child.name not in BLOCKS):
            text = _inline(child, base, links)
            if child.name == "a" and child.get("href") and text.strip():
                href = child["href"]
                if not href.startswith(("#", "javascript:", "mailto:")):
                    links.append(_unwrap(urljoin(base, href)))
                    text = f"{text}[{len(links)}]"
            out.append(text)
    return "".join(out)


def _table(table, base, links):
    rows = []
    for tr in table.find_all("tr"):
        cells = [" ".join(_inline(c, base, links, True).split())
                 for c in tr.find_all(["td", "th"])]
        if any(cells):
            rows.append(cells)
    if not rows:
        return ""
    n = max(len(r) for r in rows)
    rows = [r + [""] * (n - len(r)) for r in rows]
    widths = [min(28, max(len(r[i]) for r in rows)) for i in range(n)]
    lines = []
    for i, r in enumerate(rows):
        lines.append(" ".join(c[:w].ljust(w) for c, w in zip(r, widths)).rstrip())
        if i == 0:
            lines.append(" ".join("-" * w for w in widths))
    return "\n".join(lines)


def parse(html: str, base_url: str, reader: bool = False):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(list(SKIP) + ["nav", "footer", "aside"]):
        t.decompose()
    root = soup.body or soup
    if reader:
        root = soup.find("article") or soup.find("main") or root
    tables = [t for t in root.find_all("table") if not t.find("table")]
    table_ids = {id(t) for t in tables}
    in_table = {id(d) for t in tables for d in t.descendants}
    links, blocks = [], []
    for el in root.find_all(BLOCKS + ["table", "img"]):
        if id(el) in in_table:
            continue
        if el.name == "img":
            src = el.get("src") or ""
            if not src or src.startswith("data:"):
                src = el.get("data-src") or el.get("data-lazy-src") or el.get("data-original") or ""
            if not src and el.get("srcset"):
                src = el["srcset"].split(",")[0].split()[0]
            small = any(str(el.get(a, "")).isdigit() and int(el.get(a)) < 40 for a in ("width", "height"))
            if src and not src.startswith("data:") and not small:
                blocks.append(("img", urljoin(base_url, src)))
            continue
        if el.name == "table":
            if id(el) in table_ids:
                text = _table(el, base_url, links)
                if text:
                    blocks.append(("pre", text))
            continue
        text = _inline(el, base_url, links)
        if el.name != "pre":
            text = " ".join(text.split())
        if text.strip():
            blocks.append((el.name, text))
        if not blocks:
            blocks.append(("p", "No readable text found (blank, blocked, or JavaScript-only page)."))
    return blocks, links

def parse_forms(html: str, base_url: str):
    soup = BeautifulSoup(html, "lxml")
    forms = []
    for f in soup.find_all("form"):
        fields, text = {}, None
        for i in f.find_all("input"):
            name = i.get("name")
            kind = (i.get("type") or "text").lower()
            if not name or kind in ("submit", "button", "image", "reset", "file", "checkbox", "radio"):
                continue
            fields[name] = i.get("value", "")
            if text is None and kind in ("text", "search", "email", "url"):
                text = name
        if text:
            forms.append({
                "action": urljoin(base_url, f.get("action") or base_url),
                "method": (f.get("method") or "get").lower(),
                "fields": fields,
                "text": text,
            })
    return forms