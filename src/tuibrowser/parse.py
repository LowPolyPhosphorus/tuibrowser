from urllib.parse import urljoin

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

SKIP = {"script", "style", "noscript", "head", "svg", "template"}
BLOCKS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre"]


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
                    links.append(urljoin(base, href))
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
    for el in root.find_all(BLOCKS + ["table"]):
        if id(el) in in_table:
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
    return blocks, links