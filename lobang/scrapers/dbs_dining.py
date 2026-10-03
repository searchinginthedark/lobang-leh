"""DBS/POSB "Eat your way to deals" page: card dining privileges (1-for-1, % off, S$ off).

The page ships its cards as plain HTML inside a <noscript> block (no JSON call needed):
<div class="card card-std"> ... <h5><a href=PROMO>Merchant</a></h5><p>offer</p>.
The page lists standing offers, so there is no publish date. robots.txt: allowed.
"""

import html
import re

from lobang.net import FetchError

URL = "https://www.dbs.com.sg/personal/promotion/cards-wonderful-dining"
_CARD = re.compile(
    r'<div class="card card-std[^"]*">.*?<h5[^>]*>\s*<a href="([^"]+)"[^>]*>(.*?)</a>\s*</h5>\s*<p[^>]*>(.*?)</p>',
    re.S)
_TAGS = re.compile(r"<[^>]+>")


def _text(s):
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", s))).strip()


def parse(body):
    page = body.decode("utf-8", "replace") if isinstance(body, bytes) else body
    out, seen = [], set()
    for m in _CARD.finditer(page):
        url = html.unescape(m.group(1)).split("?")[0]
        name, offer = _text(m.group(2)), _text(m.group(3))
        if not url.startswith("https://") or not name or url in seen:
            continue
        seen.add(url)
        out.append({"title": "{0}: {1}".format(name, offer) if offer else name, "url": url,
                    "summary": "DBS/POSB card dining privilege. " + offer, "published": None})
    if not out:
        raise FetchError("dbs_dining: no card-std cards (markup changed?)")
    return out


def fetch(src, get, key):
    return parse(get(src.get("url") or URL))
