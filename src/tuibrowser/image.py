from io import BytesIO

from PIL import Image
from rich.text import Text


def to_text(data: bytes, cols: int = 60) -> Text:
    img = Image.open(BytesIO(data)).convert("RGB")
    w, h = img.size
    cols = max(8, min(cols, w))
    rows = max(2, int(h * cols / w))
    rows = min(rows + rows % 2, 80)
    img = img.resize((cols, rows), Image.LANCZOS)
    px = img.load()
    out = Text()
    for y in range(0, rows, 2):
        for x in range(cols):
            t, b = px[x, y], px[x, y + 1]
            out.append("▀", style=f"rgb({t[0]},{t[1]},{t[2]}) on rgb({b[0]},{b[1]},{b[2]})")
        out.append("\n")
    out.append("\n")
    return out
