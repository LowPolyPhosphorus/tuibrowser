from tuibrowser.parse import parse


def test_link_numbering():
    blocks, links = parse('<p>hi <a href="/x">there</a></p>', "https://a.com")
    assert links == ["https://a.com/x"]
    assert blocks == [("p", "hi there[1]")]


def test_skips_anchors_and_scripts():
    blocks, links = parse('<p>a<script>x()</script> <a href="#top">t</a></p>', "https://a.com")
    assert links == []
    assert blocks == [("p", "a t")]