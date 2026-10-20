from urllib.parse import urljoin

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

SKIP = {"script", "style", "noscript", "head", "svg", "template"}
BLOCKS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre"]


def _inline(node, base, links):
    out = []
    for child in node.children:
        if isinstance(child, Comment):
            continue
        if isinstance(child, NavigableString):
            out.append(str(child))
        elif isinstance(child, Tag) and child.name not in SKIP and child.name not in BLOCKS:
            text = _inline(child, base, links)
            if child.name == "a" and child.get("href") and text.strip():
                href = child["href"]
                if not href.startswith(("#", "javascript:", "mailto:")):
                    links.append(urljoin(base, href))
                    text = f"{text}[{len(links)}]"
            out.append(text)
    return "".join(out)


def parse(html: str, base_url: str):
    """Return (blocks, links). blocks is a list of (kind, text)."""
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(list(SKIP) + ["nav", "footer", "aside"]):
        t.decompose()
    root = soup.body or soup
    links, blocks = [], []
    for el in root.find_all(BLOCKS):
        text = _inline(el, base_url, links)
        if el.name != "pre":
            text = " ".join(text.split())
        if text.strip():
            blocks.append((el.name, text))
    return blocks, links