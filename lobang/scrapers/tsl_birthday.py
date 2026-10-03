"""TheSmartLocal "Birthday deals & freebies in Singapore" roundup (WordPress, server-rendered).

Each perk is a numbered <h3><b>N. Brand</b></h3>, then an <h4> naming the perk, prose <p>s, and
usually a labelled <p><b>Redeem on:</b> Within birthday month.</p>. That label is what makes
this source worth having: it states the redemption window in a fixed slot (33 entries,
measured 2026-10-03; Boost Juice and Tanuki Raw had none). Non-F&B entries (Uniqlo, Sephora)
are left to the classifier's F&B test. All entries share one URL, so each gets a #brand anchor
as its stable id. The old /birthday-freebies-singapore/ URL 301s here.
"""

import html
import re

from lobang.net import FetchError

URL = "https://thesmartlocal.com/read/birthday-deals-freebies-singapore/"
_H3 = re.compile(r"<h3[^>]*>(.*?)</h3>", re.S)
_H4 = re.compile(r"<h4[^>]*>(.*?)</h4>", re.S)
_P = re.compile(r"<p[^>]*>(.*?)</p>", re.S)
_NUMBERED = re.compile(r"^\d{1,2}\.\s+(.+)$")
_REDEEM = re.compile(r"^redeem (?:on|by|period)\s*:?\s*", re.I)
_SKIP = re.compile(r"^(?:find out more|full list of|read more|also read|check out)"
                   r"|image (?:credit|adapted|for illustrative)", re.I)
_TAGS = re.compile(r"<[^>]+>")


def _text(s):
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", s))).strip()


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def parse(body, url=URL):
    page = body.decode("utf-8", "replace") if isinstance(body, bytes) else body
    heads = list(_H3.finditer(page))
    out, seen = [], set()
    for i, h in enumerate(heads):
        m = _NUMBERED.match(_text(h.group(1)))
        if not m:
            continue
        brand = m.group(1).strip()
        block = page[h.end(): heads[i + 1].start() if i + 1 < len(heads) else h.end() + 20000]
        h4 = _H4.search(block)
        perk = _text(h4.group(1)) if h4 else ""
        redeem, prose = None, []
        for p in _P.finditer(block):
            t = _text(p.group(1))
            # Captions sit in their own short <p>; a long one mentioning an image is prose.
            if not t or (_SKIP.search(t) and len(t) < 200):
                continue
            if _REDEEM.match(t):
                redeem = _REDEEM.sub("", t).strip() or None
                continue
            prose.append(t)
        slug = _slug(brand)
        if not perk or not slug or slug in seen:
            continue
        seen.add(slug)
        out.append({"title": "{0}: {1}".format(brand, perk), "url": url.split("#")[0] + "#" + slug,
                    "summary": " ".join(prose), "published": None, "redeem": redeem})
    if not out:
        raise FetchError("tsl_birthday: no numbered <h3> entries (markup changed?)")
    if not any(o["redeem"] for o in out):
        # The label is the point of this source; losing it everywhere means the markup moved.
        raise FetchError("tsl_birthday: no 'Redeem on:' lines (markup changed?)")
    return out


def fetch(src, get, key):
    u = src.get("url") or URL
    return parse(get(u), u)
