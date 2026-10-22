from pathlib import Path
from urllib.parse import quote_plus, urlencode

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Input, Static

from .fetch import fetch
from .parse import parse, parse_forms

BOOKMARKS = Path.home() / ".tuibrowser_bookmarks"


def build(blocks, sel: int = 0) -> Text:
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
    if sel:
        out.highlight_regex(rf"\[{sel}\]", "bold reverse")
    return out


class Browser(App):
    CSS = """
    #url { dock: top; display: none; }
    #page { padding: 0 2; }
    #status { dock: bottom; height: 1; background: $accent; padding: 0 1; }
    #find { dock: top; display: none; }
    #fpr, { dock: top; display: none; }
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
        ("slash", "find", "Find"),
        ("n", "next_match", "Next match"),
        ("N", "prev_match", "Prev match"),
        ("question_mark", "show_help", "Help"),
        ("e", "toggle_reader", "Reader mode"),
        ("v", "view_source", "View source"),
        ("i", "fill_form", "Fill form"),
        Binding("tab", "next_link", "Next Link", priority=True),
        Binding("shift+tab", "prev_link", "Prev link", priority=True),
    ]

    def __init__(self, start_url: str):
        super().__init__()
        self.start_url = start_url
        self.url = ""
        self.links: list[str] = []
        self.history: list[str] = []
        self.forward: list[str] = []
        self.matches: list[int] = []
        self.reader = False
        self.sel = 0
        self.blocks = []
        self.forms = []
        self.match_i = -1
        self.buffer = ""

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Enter URL and press Enter", id="url")
        yield Input(placeholder="Find in page", id="find")
        yield Input(placeholder="Form text (enter to submit)", id="form")
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
    def load(self, url: str, push: bool = True, data=None) -> None:
        self.forms = []
        if url == "about:bookmarks":
            urls = BOOKMARKS.read_text().split() if BOOKMARKS.exists() else []
            blocks = [("h1", "Bookmarks")] + [("li", f"{u}[{i}]") for i, u in enumerate(urls, 1)]
            self.call_from_thread(self.show, url, blocks, urls, push)
            return
        if url.startswith("view-source:"):
            try:
                _, raw = fetch(url[len("view-source:"):])
            except Exception as e:
                self.call_from_thread(self.set_status, f"Error: {e}")
                return
            self.call_from_thread(self.show, url, [("pre", raw[:200000])], [], push)
            return
        self.call_from_thread(self.set_status, f"Loading {url} ...")
        try:
            final, html = fetch(url)
            blocks, links = parse(html, final, self.reader)
            self.forms = parse_forms(html, final)
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
        self.blocks = blocks
        self.sel = 0
        self.lines = build(blocks).plain.split("\n")
        self.query_one("#content", Static).update(build(blocks))
        self.query_one("#page").scroll_home(animate=False)
        form_hint = "i:form  " if self.forms else ""
        self.set_status(f"{self.url} | {len(links)} links | g:url  #+Enter:follow  {form_hint}b:back  q:quit  ?:help")

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

    def action_toggle_reader(self) -> None:
        self.reader = not self.reader
        if self.url and not self.url.startswith("about:"):
            self.load(self.url, push=False)

    def action_view_source(self) -> None:
        if self.url and not self.url.startswith(("about:", "view-source:")):
            self.load("view-source:" + self.url)

    def action_fil_form(self) -> None:
        if not self.forms:
            self.set_status("No form with a text box on this page")
            return
        box = self.query_one("#form", Input)
        box.placeholder = f"{self.forms[0]['text']}: (Enter to submit)"
        box.display = True
        box.value = ""
        box.focus()

    def action_next_link(self) -> None:
        self._select(1)

    def action_prev_link(self) -> None:
        self._select(-1)

    def _select(self, step: int) -> None:
        if any(self.query_one(i, Input).has_focus for i in ("#url", "#find", "#form")):
            return
        n = len(self.links)
        if not n:
            return
        if self.sel == 0:
            self.sel = 1 if step > 0 else n
        else:
            self.sel = (self.sel + step - 1) % n + 1
        self.buffer = ""
        self.query_one("#content", Static).update(build(self.blocks, self.sel))
        self.query_one("#page").scroll_to(y=max(0, self._line_of(self.sel) - 3), animate=False)
        self.set_status(f"[{self.sel}] {self.links[self.sel - 1]} (Enter: follow)")

    def _line_of(self, n: int) -> int:
        width = max(self.query_one("#content").size.width, 20)
        y = 0
        for line in self.lines:
            if f"[{n}]" in line:
                return y
            y += max(1, -(-len(line) // width))
        return 0

    def action_show_help(self) -> None:
        self.notify(
            "j/k scroll | d/u page | g url/search | #+Enter follow | b/f back/fwd | "
            "r reload | / find, n/N next/prev | m/o bookmarks | q quit",
            timeout=10,
        )
            
    def action_find(self) -> None:
        box = self.query_one("#find", Input)
        box.display = True
        box.value = ""
        box.focus()

    def action_next_match(self) -> None:
        self._goto_match(1)

    def action_prev_match(self) -> None:
        self._goto_match(-1)

    def _goto_match(self, step: int) -> None:
        if not self.matches:
            self.set_status("No matches")
            return
        self.match_i = (self.match_i +step) % len(self.matches)
        self.query_one("#page").scroll_to(y=self.matches[self.match_i], animate=False)
        self.set_status(f"match {self.match_i + 1}/{len(self.matches)}")

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
        if not text:
            return
        if event.input.id == "form":
            f = self.forms[0]
            data = dict(f["fields"])
            data[f["text"]] = text
            if f["method"] == "post":
                self.load(f["action"], data=data)
            else:
                sep = "&" if "?" in f["action"] else "?"
                self.load(f["action"] + sep + urlencode(data))
            return
        if event.input.id == "find":
            q = text.lower()
            self.matches = [i for i, l in enumerate(self.lines) if q in l.lower()]
            self.match_i = -1
            self.action_next_match()
            return
        if " " in text or ("." not in text and "://" not in text):
            text = "https://html.duckduckgo.com/html/?q=" + quote_plus(text)
        self.load(text)

    # --- link numbers: type digits, press Enter ---
    def on_key(self, event) -> None:
        if any(self.query_one(i, Input).has_focus for i in ("#url", "#find", "#form")):
            return
        if event.key.isdigit():
            self.buffer += event.key
            n = int(self.buffer)
            target = self.links[n - 1] if 1 <= n <= len(self.links) else "no such link"
            self.set_status(f"link {n}: {target}  (Enter: follow, Esc: cancel)")
        elif event.key == "enter" and self.sel and not self.buffer:
            self.load(self.links[self.sel - 1])
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