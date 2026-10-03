"""misslobang.com category listings (Next.js app router, no RSS).

The category pages are server-rendered: every article is an <a class="group flex ..."> card
holding an <h3> headline, a <p> standfirst, a deal badge ("1-for-1 + free gift") and, on some
cards, the publish date. Registry `url` picks the category (/category/food, /category/deals).
No robots restriction (robots.txt: Allow: /).
"""

import html
import re
from datetime import datetime, timedelta

from lobang.net import FetchError
from lobang.textutil import SGT, now_sgt

BASE = "https://www.misslobang.com"
_CARD = re.compile(r'<a class="group flex[^"]*"[^>]*href="(/article/[^"#?]+)"')
_H3 = re.compile(r"<h3[^>]*>(.*?)</h3>", re.S)
_P = re.compile(r'<p class="text-sm text-gray-500[^"]*">(.*?)</p>', re.S)
_BADGE = re.compile(r'<span class="text-xs font-semibold text-accent[^"]*">(.*?)</span>', re.S)
_DATE = re.compile(r"</svg>(\d{1,2} [A-Z][a-z]{2} 20\d\d)</span>")
_TAGS = re.compile(r"<[^>]+>")


def _text(s):
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", s))).strip()


def parse(body, now=None, max_age_days=60, limit=80):
    page = body.decode("utf-8", "replace") if isinstance(body, bytes) else body
    starts = [(m.start(), m.group(1)) for m in _CARD.finditer(page)]
    if not starts:
        raise FetchError("misslobang: no article cards (markup changed?)")
    now = now or now_sgt()
    out, seen = [], set()
    for i, (pos, path) in enumerate(starts):
        block = page[pos: starts[i + 1][0] if i + 1 < len(starts) else pos + 12000]
        h3 = _H3.search(block)
        if not h3 or path in seen:
            continue
        seen.add(path)
        pub = None
        dm = _DATE.search(block)
        if dm:
            try:
                pub = datetime.strptime(dm.group(1), "%d %b %Y").replace(tzinfo=SGT)
            except ValueError:
                pub = None
        if pub and now - pub > timedelta(days=max_age_days):
            continue
        p = _P.search(block)
        badge = _BADGE.search(block)
        summary = " ".join(x for x in (_text(badge.group(1)) if badge else "", _text(p.group(1)) if p else "") if x)
        out.append({"title": _text(h3.group(1)), "url": BASE + path, "summary": summary, "published": pub})
        if len(out) >= limit:
            break
    if not out:
        raise FetchError("misslobang: cards found but none parsed (markup changed?)")
    return out


def fetch(src, get, key):
    return parse(get(src.get("url") or BASE + "/category/food"))
