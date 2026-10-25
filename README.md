# tuibrowser

A text-mode web browser for your terminal, built with Python and Textual.

## Features

* **Browsing**
    * Terminal web browsing with numbered links
    * Back / forward history
    * URL bar, find-in-page (`1`), and view source
    * Bookmarks
    * Reader mode for stripping a page down to its article text 

* **Tabs**
    * Multi-tab support
    * Open a new tab with `t`, close the current tab with `w`
    * Switch tabs with `]` and `[`

* **Forms and search** **
    * Fill in a pages's text form from inside the TUI (`i`)
    * Type a query into the adress bar to search with your default engine (DuckDuckGo by default)

* **Images**
    * Inline images are rendered as text
    * In layout mode, click an `[img]` marker to open the image in a popup

* **Layout mode** (`l`)**
    * Renders the page roughly as a real browser would lay it out, with sidebars and columns in place
    * Click links and image markers with the mouse
    * Needs Playwright (see below)

* **JS mode** (`J`)**
    * Loads pages in a headless browser so JS rendered sites work
    * Needs playwright (see below)

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

** : Beta feature W.I.P.

> MIT [LICENSE](/LICENSE)