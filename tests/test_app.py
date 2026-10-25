import asyncio

from tuibrowser import app as appmod

HTML = '<h1>Hi</h1><p><a href="/a">one</a> <a href="/b">two</a></p>'


def fake_fetch(url, data=None):
    return url, HTML


def test_startup_hides_input_and_parses_links(monkeypatch):
    monkeypatch.setattr(appmod, "fetch", fake_fetch)

    async def go():
        a = appmod.Browser("https://a.com")
        async with a.run_test() as pilot:
            await pilot.pause(0.5)
            assert a.links == ["https://a.com/a", "https://a.com/b"]
            for box in ("#url", "#find", "#form"):
                assert not a.query_one(box).display

    asyncio.run(go())


def test_follow_link_by_number_and_bakc(monkeypatch):
    monkeypatch.setattr(appmod, "fetch", fake_fetch)

    async def go():
        a = appmod.Browser("https://a.com")
        async with a.run_test() as pilot:
            await pilot.pause(0.5)
            await pilot.press("2", "enter")
            await pilot.pause(0.5)
            assert a.url == "https://a.com/b"
            assert a.history == ["https://a.com"]
            await pilot.press("b")
            await pilot.pause(0.5)
            assert a.url == "https://a.com"

    asyncio.run(go())

def test_tabs_open_and_close(monkeypatch):
    monkeypatch.setattr(appmod, "fetch", fake_fetch)

    async def go():
        a = appmod.Browser("https://a.com")
        async with a.run_test() as pilot:
            await pilot.pause(0.5)
            await pilot.press("t")
            await pilot.pause(0.5)
            assert len(a.tabs) == 2 and a.cur == 1
            await pilot.press("w")
            await pilot.pause(0.2)
            assert len(a.tabs) == 1

    asyncio.run(go())

def test_config_defaults():
    assert appmod.DEFAULTS["start_page"].startswith("https://")
    assert "link_color" in appmod.load_config()