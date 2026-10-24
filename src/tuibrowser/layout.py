from rich.text import Text

from .parse import _unwrap

CELL_W = 8
CELL_H = 22

def prepare(items):
    nums, links, last = {}, [], {}
    for i, it in enumerate(items):
        href, aid = it.get("href"), it.get("aid")
        if aid is None or not href:
            it["n"] = 0
            continue
        if aid not in nums:
            links.append(_unwrap(href))
            nums[aid] = len(links)
        it["n"] = nums[aid]
        last[aid] = i
    for i in last.values():
        items[i]["tag"] = True
    items.sort(key=lambda it: (it["y"], it["x"]))
    return items, links


def render(items, cols, link_style, sel=0):
    rows, marks = {}, {}
    for it in items:
        text = it["text"] + (f"[{it['n']}]" if it.get("tag") else "")
        row = max(0, round(it["y"] / CELL_H))
        col = max(0, round(it["x"] / CELL_W))
        text = text[: max(0, cols - col)]
        if not text:
            continue
        while True:
            line = rows.setdefault(row, [" "] * cols)
            c = next(
                (c for c in range(col, col + 9)
                 if c + len(text) <= cols and all(x == " " for x in line[c:c + len(text)])),
                 None,
            )
            if c is not None:
                break
            row += 1
        line[c:c + len(text)] = list(text)
        style = "bold" if it.get("b") else ""
        if it["n"]:
            style = "bold reverse" if it["n"] == sel else link_style
        marks.setdefault(row, []).append((c, len(text), style, it["n"]))
    out = Text()
    for r in range(max(rows) + 1 if rows else 0):
        start = len(out)
        out.append("".join(rows.get(r, [])).rstrip() + "\n")
        for c, ln, style, n in marks.get(r, []):
            if style:
                out.stylize(style, start + c, start + c + ln)
            if n:
                out.apply_meta({"@click": f"app.follow_link({n})"}, start + c, start + c + ln)
    return out