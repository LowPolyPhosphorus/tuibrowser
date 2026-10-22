# tuibrowser

A text-mode web browser for your terminal, built with Python and Textual.

## Features

* Core features
    * terminal web browsing
    * numbered link navigation
    * back history
    * URL & find bar

* Tab system
  * mult-tab support
  * tab shortcuts
    * open a new tab with t
    * close the current tavb b with x  
  
* Forms/search
  * form submission: interact with web forms and inputs inside the tui
  * search integration: type a query into the address bar to query the default search engine (DuckDuckGo by default) 

* Customization
  * config file support: fully configurable via a simple TOML file in your home directory.
    * `start_page`: set preferred homepage URL
    * `search_url`: change your default search engine query URL
    * `link_color`: customize the terminal color/style of link markers

## Install
```
git clone https://github.com/LowPolyPhosphorus/tuibrowser
cd tuibrowser
pip install -e .
tuibrowser https://text.npr.org
```

## Keys
| Key | Action |
|---|---|
| `j` / `k` | sroll down / up |
| `d` / `u` | page down / up |
| `g` / `/` | open URL bar (or search) |
| number + `Enter` | follow link |
| `b` / `f` | back / forward |
| `r` | reload |
| `m` / `o` | bookmark / list bookmarks |
| `t` | open new tab |
| `x` | close current tab |
| `q` | quit |
