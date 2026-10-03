"""HungryGoWhere homepage: latest food news cards, many tagged "New Openings".

The RSS and /food-news/ listing both answer HTTP 500, but the homepage is server-rendered.
Card: <div class="card h-100"> ... <span class="tag">New Openings</span> ... <h3 class="card-title">
... <span class="dated">Oct 2, 2026</span>. robots.txt only disallows */page/*.
"""

import html
import re
from datetime import datetime

from lobang.net import FetchError
from lobang.textutil import SGT

URL = "https://www.hungrygowhere.com/"
_CARD = re.compile(r'<div class="card h-100">')
_LINK = re.compile(r'<a href="(https://hungrygowhere\.com/[^"]+)">\s*<h3 class="card-title">(.*?)</h3>', re.S)
_TAG = re.compile(r'<span class="tag">(.*?)</span>', re.S)
_DATED = re.compile(r'<span class="dated">\s*([A-Z][a-z]{2} \d{1,2}, 20\d\d)\s*</span>')
_TAGS = re.compile(r"<[^>]+>")


def _text(s):
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", s))).strip()


def parse(body):
    page = body.decode("utf-8", "replace") if isinstance(body, bytes) else body
    starts = [m.start() for m in _CARD.finditer(page)]
    out, seen = [], set()
    for i, pos in enumerate(starts):
        block = page[pos: starts[i + 1] if i + 1 < len(starts) else pos + 4000]
        link = _LINK.search(block)
        if not link or link.group(1) in seen:
            continue
        seen.add(link.group(1))
        tag, dated = _TAG.search(block), _DATED.search(block)
        pub = None
        if dated:
            try:
                pub = datetime.strptime(dated.group(1), "%b %d, %Y").replace(tzinfo=SGT)
            except ValueError:
                pub = None
        out.append({"title": _text(link.group(2)), "url": link.group(1),
                    "summary": _text(tag.group(1)) if tag else "", "published": pub})
    if not out:
        raise FetchError("hungrygowhere: no card-title cards (markup changed?)")
    return out


def fetch(src, get, key):
    return parse(get(src.get("url") or URL))
