# tuibrowser

A text-mode web browser for your terminal, built with Python and Textual.

## Features

* **Browsing**
    * Terminal web browsing with numbered links
    * Back / forward history
    * URL bar, find-in-page (`/`), and view source
    * Bookmarks
    * Reader mode for stripping a page down to its article text

<img src="https://user-cdn.hackclub-assets.com/01a171af-c43b-7d16-8064-304d4157176f/Screenshot%202026-10-24%20231121.png" alt="Browsing a page in tuibrowser" width="800">

* **Tabs**
    * Multi-tab support
    * Open a new tab with `t`, close the current tab with `w`
    * Switch tabs with `]` and `[`

<img src="https://user-cdn.hackclub-assets.com/01a171b0-eb39-7bb8-9f77-a789fdbafb2a/Screenshot%202026-10-24%20231246.png" alt="Multiple tabs in tuibrowser" width="800">

* **Forms and search** \*\*
    * Fill in a page's text form from inside the TUI (`i`)
    * Type a query into the address bar to search with your default engine (DuckDuckGo by default)

* **Images**
    * Inline images are rendered as text
    * In layout mode, click an `[img]` marker to open the image in a popup

<img src="https://user-cdn.hackclub-assets.com/01a171b1-c66e-7cd9-b95b-856de06312b0/Screenshot%202026-10-24%20231342.png" alt="Inline images rendered as text" width="800">

* **Layout mode** (`L`) \*\*
    * Renders the page roughly as a real browser would lay it out, with sidebars and columns in place
    * Click links and image markers with the mouse
    * Needs Playwright (see below)

<img src="https://user-cdn.hackclub-assets.com/01a171b3-7ad3-7ecb-a561-2e5e1e3b8ec5/Screenshot%202026-10-24%20231519.png" alt="Layout mode showing a Wikipedia page" width="800">

* **JS mode** (`J`) \*\*
    * Loads pages in a headless browser so JS-rendered sites work
    * Needs Playwright (see below)

<img src="https://user-cdn.hackclub-assets.com/01a171b4-fa32-7dcb-9a1e-5f19b5c1aa26/Screenshot%202026-10-24%20231707.png" alt="JS mode rendering a JavaScript site" width="800">

* **Customization**
    * Configure it with a TOML file at `~/.tuibrowser.toml`:
        * `start_page`: your preferred homepage URL
        * `search_url`: the query URL of your default search engine
        * `link_color`: the terminal style of link markers
        * `images`: set to `false` to turn off inline images

## Install
```
git clone https://github.com/LowPolyPhosphorus/tuibrowser
cd tuibrowser
pip install -e .
tuibrowser https://example.com
```

JS mode and layout mode need Playwright:

```
pip install playwright
playwright install chromium
```

## Keys

| Key | Action |
|---|---|
| `j` / `k` | scroll down / up |
| `d` / `u` | page down / up |
| `g` | open URL bar (or type a search) |
| number + `Enter` | follow link |
| `Tab` / `Shift+Tab` | select next / previous link, then `Enter` to follow |
| `b` / `f` | back / forward |
| `r` | reload |
| `/` | find in page |
| `n` / `N` | next / previous match |
| `m` / `o` | bookmark this page / open bookmarks |
| `t` | open new tab |
| `w` | close current tab |
| `]` / `[` | next / previous tab |
| `i` | fill in the page's form |
| `e` | toggle reader mode |
| `J` | toggle JS mode |
| `L` | toggle layout mode |
| `v` | view page source |
| `?` | help |
| `q` | quit |

Bookmarks are stored in `~/.tuibrowser_bookmarks`.

\*\* : Beta feature W.I.P.

> MIT [LICENSE](/LICENSE)