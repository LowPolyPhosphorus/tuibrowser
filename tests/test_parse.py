from tuibrowser.parse import parse


def test_link_numbering():
    blocks, links = parse('<p>hi <a href="/x">there</a></p>', "https://a.com")
    assert links == ["https://a.com/x"]
    assert blocks == [("p", "hi there[1]")]


def test_skips_anchors_and_scripts():
    blocks, links = parse('<p>a<script>x()</script> <a href="#top">t</a></p>', "https://a.com")
    assert links == []
    assert blocks == [("p", "a t")]

def text_table_renders_as_grid():
    html = "<table><tr><th>a</th><th>b</th></tr><tr><td>1</td><td>2</td></tr></table>"
    blocks, _ = parse(html, "https://a.com")
    assert blocks == [("pre", "a b\n- -\n1 2")]