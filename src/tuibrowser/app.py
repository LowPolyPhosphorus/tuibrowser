from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Input, Static
from urllib.parse import quote_plus
from pathlib import Path

BOOKMARKS = Path.home() / ".tuibrowser_bookmarks"

from .fetch import fetch
from .parse import parse


def build(blocks) -> Text:
    out = Text()
    for kind, text in blocks:
        if kind.startswith("h"):
            out.append(text.upper() + "\n\n", style="bold yellow")
        elif kind == "li":
            out.append("  • " + text + "\n")
        elif kind == "pre":
            out.append(text + "\n\n", style="dim")
        else:
            out.append(text + "\n\n")
    out.highlight_regex(r"\[\d+\]", "bold cyan")
    return out


class Browser(App):
    CSS = """
    #url { dock: top; display: none; }
    #page { padding: 0 2; }
    #status { dock: bottom; height: 1; background: $accent; padding: 0 1; }
    """
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("j", "down", "Down"),
        ("k", "up", "Up"),
        ("g", "open_url", "Go to URL"),
        ("b", "back", "Back"),
        ("r", "reload", "Reload"),
        ("d", "page down", "Page down"),
        ("u", "page up", "Page up"),
        ("f", "forward", "Forward"),
        ("m", "bookmark", "Bookmarks"),
    ]

    def __init__(self, start_url: str):
        super().__init__()
        self.start_url = start_url
        self.url = ""
        self.links: list[str] = []
        self.history: list[str] = []
        self.forward: list[str] = []
        self.buffer = ""

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Enter URL and press Enter", id="url")
        with VerticalScroll(id="page"):
            yield Static("", id="content")
        yield Static("", id="status")

    def on_mount(self) -> None:
        self.query_one("#page").focus()
        self.load(self.start_url)

    def set_status(self, msg: str) -> None:
        self.query_one("#status", Static).update(Text(msg))

    # --- loading ---
    @work(thread=True, exclusive=True)
    def load(self, url: str, push: bool = True) -> None:
        if url == "about:bookmarks":
            urls = BOOKMARKS.read_text().split() if BOOKMARKS.exists() else []
            blocks = [("h1", "Bookmarks")] + [("li", f"{u}[{i}]") for i, u in enumerate(urls, 1)]
            self.call_from_thread(self.show, url, blocks, urls, push)
            return
        self.call_from_thread(self.set_status, f"Loading {url} ...")
        try:
            final, html = fetch(url)
            blocks, links = parse(html, final)
        except Exception as e:
            self.call_from_thread(self.set_status, f"Error: {e}")
            return
        self.call_from_thread(self.show, final, blocks, links, push)

    def show(self, url, blocks, links, push) -> None:
        if push and self.url:
            self.history.append(self.url)
        if push:
            self.forward.clear()
        self.url, self.links = url, links
        self.query_one("#content", Static).update(build(blocks))
        self.query_one("#page").scroll_home(animate=False)
        self.set_status(f"{url} | {len(links)} links | g:url  number+Enter:follow  b:back  q:quit")

    # --- actions ---
    def action_down(self) -> None:
        self.query_one("#page").scroll_down()

    def action_up(self) -> None:
        self.query_one("#page").scroll_up()

    def action_open_url(self) -> None:
        box = self.query_one("#url", Input)
        box.display = True
        box.value = ""
        box.focus()

    def action_back(self) -> None:
        if self.history:
            self.forward.append(self.url)
            self.load(self.history.pop(), push=False)

    def action_forward(self) -> None:
        if self.forward:
            self.history.append(self.url)
            self.load(self.forward.pop(), push=False)

    def action_bookmark(self) -> None:
        if self.url and not self.url.startswith("about:"):
            with BOOKMARKS.open("a") as f:
                f.write(self.url + "\n")
            self.set_status(f"Bookmarked {self.url}")

    def action_bookmarks(self) -> None:
        self.load("about:bookmarks")

    def action_reload(slef) -> None:
        if self.url:
            self.load(self.url, push=False)

    def action_page_down(self) -> None:
        self.query_one("#page").scroll_page_down()

    def action_page_up(self) -> None:
        self.query_one("#page").scroll_page_up()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.input.display = False
        self.query_one("#page").focus()
        text = event.value.strip()
        if text:
            if " " in text or ("." not in text and "://" not in text):
                text = "https://html.duckduckgo.com/html/?q=" + quote_plus(text)
            self.load(text)

    # --- link numbers: type digits, press Enter ---
    def on_key(self, event) -> None:
        if self.query_one("#url", Input).has_focus:
            return
        if event.key.isdigit():
            n = int(self.buffer)
            target = self.links[n - 1] if 1 <= n <= len(self.links) else "no such link"
            self.set_status(f"link {n}: {target}  (Enter: follow, Esc: cancel)")
            self.set_status(f"{url} | {len(links)} links | g:url/search  #+Enter:follow  b:back  r:reload  d/u:page  q:quit")
        elif event.key == "enter" and self.buffer:
            n, self.buffer = int(self.buffer), ""
            if 1 <= n <= len(self.links):
                self.load(self.links[n - 1])
            else:
                self.set_status(f"No link {n}")
        elif event.key == "escape":
            self.buffer = ""
            self.set_status(self.url)

def main():
    import sys
    Browser(sys.argv[1] if len(sys.argv) > 1 else "https://text.npr.org").run()