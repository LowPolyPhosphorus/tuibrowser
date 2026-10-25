import re
import tomllib

from pathlib import Path
from urllib.parse import quote_plus, unquote, urlencode, urlparse

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Input, Static
from textual.screen import ModalScreen
from concurrent.futures import ThreadPoolExecutor

from .fetch import close_js, fetch, fetch_image, fetch_js, fetch_layout
from .image import to_text
from .layout import CELL_H, HITS, STRETCH, prepare, render as render_layout
from .parse import parse, parse_forms

BOOKMARKS = Path.home() / ".tuibrowser_bookmarks"


CONFIG = Path.home() / ".tuibrowser.toml"
DEFAULTS = {
    "start_page": "https://text.npr.org",
    "search_url": "https://html.duckduckgo.com/html?q=",
    "link_color": "bold cyan",
    "images": True,
}


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    try:
        cfg.update(tomllib.loads(CONFIG.read_text(encoding="utf-8")))
    except (OSError, tomllib.TOMLDecodeError):
        pass
    return cfg


CFG = load_config()


TAB_FIELDS = ("url", "links", "history", "forward", "blocks", "lines", 
              "sel", "forms", "matches", "match_i")

def build(blocks, sel: int = 0) -> Text:
    if blocks and blocks[0][0] == "layout":
        items, cols = blocks[0][1]
        return render_layout(items, cols, CFG["link_color"], sel)
    out = Text()
    for kind, text in blocks:
        if kind.startswith("h"):
            out.append(text.upper() + "\n\n", style="bold yellow")
        elif kind == "li":
            out.append("  • " + text + "\n")
        elif kind == "pre":
            out.append(text + "\n\n", style="dim")
        elif kind == "img":
            out.append_text(text)
        else:
            out.append(text + "\n\n")
    out.highlight_regex(r"\[\d+\]", CFG["link_color"])
    for m in re.finditer(r"\S*\[(\d+)\]", out.plain):
        out.apply_meta({"@click": f"app.follow_link({m.group(1)})"}, m.start(), m.end())
    if sel:
        out.highlight_regex(rf"\[{sel}\]", "bold reverse")
    return out


class ImageScreen(ModalScreen):
    BINDINGS = [("escape", "close", "Close")]
    DEFAULT_CSS = """
    #imgbox { width: 92%; height: 92%; border: round $accent; background: $surface; }
    """

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="imgbox"):
            yield Static("Loading image ...", id="imgview")

    def on_mount(self) -> None:
        self.load_image(self.query_one("#imgview", Static))

    @work(thread=True)
    def load_image(self, view: Static) -> None:
        width = max(20, min(self.app.size.width - 8, 100))
        try:
            out = to_text(fetch_image(self.url), width)
        except Exception as e:
            out = Text(f"Could not load image: {e}")
        self.app.call_from_thread(view.update, out)

    def action_close(self) -> None:
        self.dismiss()


class Browser(App):
    CSS = """
    #url { dock: top; display: none; }
    #page { padding: 0 2; }
    #status { dock: bottom; height: 1; background: $accent; padding: 0 1; }
    #find { dock: top; display: none; }
    #fpr { dock: top; display: none; }
    #tabs { height: 1; background: $panel; }
    #form { dock: top; display: none; }
    """
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("j", "down", "Down"),
        ("k", "up", "Up"),
        ("g", "open_url", "Go to URL"),
        ("b", "back", "Back"),
        ("r", "reload", "Reload"),
        ("d", "page_down", "Page down"),
        ("u", "page_up", "Page up"),
        ("f", "forward", "Forward"),
        ("m", "bookmark", "Bookmarks"),
        ("o", "bookmarks", "Open bookmarks"),
        ("slash", "find", "Find"),
        ("n", "next_match", "Next match"),
        ("N", "prev_match", "Prev match"),
        ("question_mark", "show_help", "Help"),
        ("e", "toggle_reader", "Reader mode"),
        ("J", "toggle_js", "JS mode"),
        ("L", "toggle_layout", "Layout mode"),
        ("v", "view_source", "View source"),
        ("i", "fill_form", "Fill form"),
        ("t", "new_tab", "New tab"),
        ("w", "close_tab", "Close tab"),
        ("right_square_bracket", "next_tab", "Next tab"),
        ("left_square_bracket", "prev_tab", "Prev. tab"),
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
        self.blocks = []
        self.forms = []
        self.lines = []
        self.tabs = [{}]
        self.cur = 0
        self.gen = 0
        self.sel = 0
        self.match_i = -1
        self.buffer = ""
        self.reader = False
        self.js = False
        self.layout_on = False

    def compose(self) -> ComposeResult:
        yield Static("", id="tabs")
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
        gen = self.gen
        if url == "about:bookmarks":
            urls = BOOKMARKS.read_text().split() if BOOKMARKS.exists() else []
            blocks = [("h1", "Bookmarks")] + [("li", f"{u}[{i}]") for i, u in enumerate(urls, 1)]
            self.call_from_thread(self._deliver, gen, url, blocks, urls, push)
            return
        if url.startswith("view-source:"):
            try:
                _, raw = fetch(url[len("view-source:"):])
            except Exception as e:
                self.call_from_thread(self.set_status, f"Error: {e}")
                return
            self.call_from_thread(self._deliver, gen, url, [("pre", raw[:200000])], [], push)
            return
        self.call_from_thread(self.set_status, f"Loading {url} ...")
        try:
            final, html = fetch_js(url) if self.js else fetch(url, data)
            html = html[:1_500_000]
            blocks, links = parse(html, final, self.reader)
            if CFG["images"]:
                blocks = self._with_images(blocks)
            else:
                blocks = [b for b in blocks if b[0] != "img"]
            self.forms = parse_forms(html, final)
            if self.layout_on:
                cols = max(self.size.width - 10, 40)
                final, items, html = fetch_layout(url, int(cols / STRETCH))
                if not items:
                    raise RuntimeError("Layout mode found no text on this page")
                items, links = prepare(items)
                self.forms = parse_forms(html[:1_500_000], final)
                self.call_from_thread(self._deliver, gen, final, [("layout", (items, cols))], links, push)
                return
        except Exception as e:
            self.call_from_thread(self.set_status, f"Error loading {url}: {e}")
            self.call_from_thread(self._deliver, gen, url, [("h1", "Error"), ("p", str(e))], [], False)
            return
        self.call_from_thread(self._deliver, gen, final, blocks, links, push)

    def _with_images(self, blocks):
        urls = [t for k, t in blocks if k == "img" and ".svg" not in t.lower()][:14]
        if not urls:
            return [b for b in blocks if b[0] != "img"]
        width = max(20, min(self.size.width - 6, 70))
        errs = []

        def get(u):
            try:
                return to_text(fetch_image(u), width)
            except Exception as e:
                errs.append(f"{type(e).__name__}: {str(e)[:70]}")
                return None

        with ThreadPoolExecutor(6) as ex:
            done = dict(zip(urls, ex.map(get, urls)))
        shown, out = 0, []
        for kind, text in blocks:
            if kind != "img":
                out.append((kind, text))
            elif done.get(text) is not None and shown < 6:
                shown += 1
                out.append((kind, done[text]))
        why = f" ({errs[0]})" if errs else ""
        self.call_from_thread(self.notify, f"Images: {shown} shown, {len(errs)} of {len(urls)} failed{why}")
        return out

    def show(self, url, blocks, links, push) -> None:
        if push and self.url:
            self.history.append(self.url)
        if push:
            self.forward.clear()
        self.url, self.links = url, links
        self.blocks = blocks
        self.sel = 0
        text = build(blocks)
        self.lines = text.plain.split("\n")
        self.query_one("#content", Static).update(text)
        self.query_one("#page").scroll_home(animate=False)
        form_hint = "i:form  " if self.forms else ""
        self.set_status(f"{self.url} | {len(links)} links | g:url  #+Enter:follow  {form_hint}b:back  q:quit  ?:help")
        self._render_tabs()

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

    def action_toggle_js(self) -> None:
        self.js = not self.js
        self.set_status("JS mode ON (slower)" if self.js else "JS mode off")
        if self.url and not self.url.startswith("about:"):
            self.load(self.url, push=False)

    def action_toggle_layout(self) -> None:
        self.layout_on = not self.layout_on
        self.set_status("Layout mode ON (slow)" if self.layout_on else "Layout mode off")
        if self.url and not self.url.startswith(("about:", "view-source:")):
            self.load(self.url, push=False)

    def action_view_source(self) -> None:
        if self.url and not self.url.startswith(("about:", "view-source:")):
            self.load("view-source:" + self.url)

    def _deliver(self, gen, *args) -> None:
        if gen == self.gen:
            self.show(*args)

    def _render_tabs(self) -> None:
        bar = Text()
        for i, st in enumerate(self.tabs):
            url = self.url if i == self.cur else st.get("url", "")
            label = urlparse(url).netloc or url or "new"
            bar.append(f" {i + 1}:{label[:18]} ", style="bold reverse" if i == self.cur else "")
        if self.js:
            bar.append(" JS ", style="bold black on yellow")
        if self.layout_on:
            bar.append(" LAYOUT ", style="bold black on green")
        self.query_one("#tabs", Static).update(bar)

    def _save_tab(self) -> None:
        st = {k: getattr(self, k) for k in TAB_FIELDS}
        st["scroll"] = self.query_one("#page").scroll_y
        self.tabs[self.cur] = st

    def _restore_tab(self) -> None:
        self.gen += 1
        self.buffer = ""
        st = self.tabs[self.cur] or {
            "url": "", "links": [], "history": [], "forward": [], "blocks": [],
            "lines": [], "sel": 0, "forms": [], "matches": [], "match_i": -1, "scroll": 0,
        }
        for k in TAB_FIELDS:
            setattr(self, k, st[k])
        self.query_one("#content", Static).update(build(self.blocks, self.sel))
        self.call_after_refresh(
            lambda: self.query_one("#page").scroll_to(y=st["scroll"], animate=False)
        )
        self.set_status(self.url or "new tab")
        self._render_tabs()

    def _switch(self, step: int) -> None:
        if len(self.tabs) < 2:
            return
        self._save_tab()
        self.cur = (self.cur + step) % len(self.tabs)
        self._restore_tab()

    def action_next_tab(self) -> None:
        self._switch(1)

    def action_prev_tab(self) -> None:
        self._switch(-1)

    def action_new_tab(self) -> None:
        self._save_tab()
        self.tabs.append({})
        self.cur = len(self.tabs) - 1
        self._restore_tab()
        self.load(self.start_url)

    def action_close_tab(self) -> None:
        if len(self.tabs) == 1:
            self.set_status("Last tab (q to quit)")
            return
        self.tabs.pop(self.cur)
        self.cur = min(self.cur, len(self.tabs) - 1)
        self._restore_tab()
        self._render_tabs()

    def action_fill_form(self) -> None:
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

    def action_follow_link(self, n: int) -> None:
        if 1 <= n <= len(self.links):
            self.buffer = ""
            target = self.links[n - 1]
            base, _, frag = target.partition("#")
            if frag and base == self.url.partition("#")[0] and self._jump(frag):
                return
            self.load(target)

    async def on_click(self, event) -> None:
        if len(self.screen_stack) > 1:
            return
        if (getattr(event.style, "meta", None) or {}).get("@click"):
            return
        if not (self.blocks and self.blocks[0][0] == "layout"):
            return
        region = self.query_one("#content").region
        row, col = event.screen_y - region.y, event.screen_x - region.x
        best = None
        for r, c, ln, act in HITS:
            if abs(r - row) <= 1 and c -1 <= col <= c + ln:
                if best is None or abs(r - row) < best[0]:
                    best = (abs(r - row), act)
        if best:
            await self.run_action(best[1].removeprefix("app."))
            return
        near = sorted(HITS, key=lambda h: abs(h[0] - row))[:2]
        self.set_status(f"click row {row} col {col}; nearest: " + ", ".join(f"({h[0]},{h[1]})" for h in near))

    def check_action(self, action: str, parameters) -> bool | None:
        if len(self.screen_stack) > 1:
            return action == "quit"
        return True

    def action_show_image(self, i: int) -> None:
        if not (self.blocks and self.blocks[0][0] == "layout"):
            return
        imgs = [it["img"] for it in self.blocks[0][1][0] if it.get("img")]
        if 0 <= i < len(imgs):
            self.push_screen(ImageScreen(imgs[i]))

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

    def action_reload(self) -> None:
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
            text = CFG["search_url"] + quote_plus(text)
        self.load(text)

    # --- link numbers: type digits, press Enter ---
    def on_key(self, event) -> None:
        if len(self.screen_stack) > 1:
            return
        if any(self.query_one(i, Input).has_focus for i in ("#url", "#find", "#form")):
            return
        if event.key.isdigit():
            self.buffer += event.key
            n = int(self.buffer)
            target = self.links[n - 1] if 1 <= n <= len(self.links) else "no such link"
            self.set_status(f"link {n}: {target}  (Enter: follow, Esc: cancel)")
        elif event.key == "enter" and self.sel and not self.buffer:
            self.load(self.links[self.sel])
        elif event.key == "enter" and self.buffer:
            n, self.buffer = int(self.buffer), ""
            if 1 <= n <= len(self.links):
                self.action_follow_link(n)
            else:
                self.set_status(f"No link {n}")
        elif event.key == "escape":
            self.buffer = ""
            self.set_status(self.url)

def main():
    import sys
    try:
        Browser(sys.argv[1] if len(sys.argv) > 1 else CFG["start_page"]).run()
    finally:
        close_js()