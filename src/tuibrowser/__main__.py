import sys
import textwrap

from .fetch import fetch
from .parse import parse


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    final_url, html = fetch(url)
    blocks, links = parse(html, final_url)
    for kind, text in blocks:
        if kind.startswith("h"):
            print(text.upper(), end="\n\n")
        elif kind == "li":
            print(textwrap.fill(text, 80, initial_indent="  * ", subsequent_indent="    "))
        elif kind == "pre":
            print(text, end="\n\n")
        else:
            print(textwrap.fill(text, 80), end="\n\n")
    print("Links:")
    for i, link in enumerate(links, 1):
        print(f"[{i}] {link}")


if __name__ == "__main__":
    main()