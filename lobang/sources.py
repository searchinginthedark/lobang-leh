"""Source fetchers. Each returns {ok, items, error}; a failure is never an empty list.

An item is a plain dict:
  id, source, publisher, tier, scope, title, url, summary, published (datetime SGT|None)
"""

from __future__ import annotations

import html
import importlib
import os
import re
import urllib.parse

import feedparser

from . import net
from .textutil import SGT, clip, from_struct, one_line, parse_iso, sha, strip_html

GNEWS = "https://news.google.com/rss/search?q={q}&hl=en-SG&gl=SG&ceid=SG:en"
GNEWS_WINDOW = "when:7d"


def _item(src, title, url, summary, published, publisher=None):
    title = one_line(html.unescape(title or ""))
    if not title or not url:
        return None
    return {
        "id": sha(url),
        "source": src["name"],
        "publisher": publisher or src.get("publisher") or src["name"],
        "tier": src.get("tier", "media"),
        "scope": src.get("scope", "mixed"),
        "fnb_only": bool(src.get("fnb_only")),
        # Every RSS/Telegram source in the registry is an SG publisher; Google News is global.
        "sg_source": src.get("type") != "gnews",
        "title": clip(title, 220),
        "url": url,
        "summary": clip(strip_html(summary or ""), 600),
        "published": published,
    }


def _feed(body):
    """Parsed feed, or FetchError. A Cloudflare challenge page parses as a feed with no
    entries and no bozo flag, so `version` (RSS/Atom actually recognised) is the test:
    without it a blocked source would report ok with zero items."""
    feed = feedparser.parse(body)
    if not feed.entries and (feed.bozo or not feed.get("version")):
        raise net.FetchError("not a feed: {0}".format(feed.get("bozo_exception") or "no RSS/Atom recognised"))
    return feed


def parse_rss(src, body):
    feed = _feed(body)
    out = []
    for e in feed.entries:
        pub = from_struct(e.get("published_parsed") or e.get("updated_parsed"))
        summary = e.get("summary") or ""
        it = _item(src, e.get("title"), e.get("link"), summary, pub)
        if it:
            out.append(it)
    return out


_GN_SUFFIX = re.compile(r"\s+-\s+[^-]{2,60}$")


def gnews_url(query):
    return GNEWS.format(q=urllib.parse.quote_plus("{0} {1}".format(query, GNEWS_WINDOW)))


def parse_gnews(src, body):
    feed = _feed(body)
    out = []
    for e in feed.entries:
        publisher = (e.get("source") or {}).get("title") or "Google News"
        title = e.get("title") or ""
        # Google appends " - Publisher" to every headline; it would defeat clustering.
        if title.endswith(" - " + publisher):
            title = title[: -len(publisher) - 3]
        else:
            title = _GN_SUFFIX.sub("", title)
        pub = from_struct(e.get("published_parsed"))
        # The description is just the headline again as a link; no real summary.
        it = _item(src, title, e.get("link"), "", pub, publisher=publisher)
        if it:
            out.append(it)
    return out


_TG_MSG = re.compile(r'<div class="tgme_widget_message [^"]*"[^>]*data-post="([^"]+)"')
_TG_TEXT = re.compile(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S)
_TG_TIME = re.compile(r'<time[^>]*datetime="([^"]+)"')


def _bare(line):
    """Trim emoji/punctuation from both ends, keeping inner text ("$9++ BAR BITES?!" keeps its $)."""
    s = line.strip()
    lead = re.match(r"^[^\w$]+", s, re.U)
    if lead:
        s = s[lead.end():]
    trail = re.search(r"[^\w?!.)%+]+$", s, re.U)
    if trail:
        s = s[:trail.start()]
    return s.strip()


def parse_telegram(src, body):
    page = body.decode("utf-8", "replace")
    starts = [(m.start(), m.group(1)) for m in _TG_MSG.finditer(page)]
    if not starts and "tgme_channel_info" not in page:
        raise net.FetchError("no telegram preview markup")
    out = []
    for i, (pos, post) in enumerate(starts):
        block = page[pos: starts[i + 1][0] if i + 1 < len(starts) else len(page)]
        tm = _TG_TEXT.search(block)
        if not tm:
            continue  # photo/sticker-only post
        text = strip_html(tm.group(1))
        lines = [_bare(l) for l in text.split("\n") if _bare(l)]
        if not lines:
            continue
        # Deal channels head a post with just the brand ("🍣 Sushiro 🍣"); the deal is line two.
        if len(lines) > 1 and len(lines[0]) < 28:
            lines = [lines[0] + ": " + lines[1]] + lines[2:]
        dt = _TG_TIME.search(block)
        pub = parse_iso(dt.group(1)).astimezone(SGT) if dt and parse_iso(dt.group(1)) else None
        url = "https://t.me/" + post
        it = _item(src, lines[0], url, " ".join(lines[1:]), pub)
        if it:
            out.append(it)
    return out


def run_module(src):
    """`scrape` / `api` sources: lobang/scrapers/<parser>.py owns the requests and parsing.

    Contract (docs/scrapers.md): module.fetch(src, get, key) -> list of dicts with
    title, url, summary, published (datetime or None). It must RAISE net.FetchError when
    the page/API no longer has the expected structure; returning [] means "the source
    genuinely lists nothing today", never "the markup changed".
    """
    mod = importlib.import_module("lobang.scrapers." + src["parser"])
    key = os.environ.get(src["env"]) if src.get("env") else None

    def get(url, **kw):
        kw.setdefault("ua", src.get("ua", "browser"))
        return net.get(url, **kw)

    out = []
    for r in mod.fetch(src, get, key):
        pub = r.get("published")
        if pub is not None and pub.tzinfo is None:
            pub = pub.replace(tzinfo=SGT)
        it = _item(src, r.get("title"), r.get("url"), r.get("summary") or "",
                   pub.astimezone(SGT) if pub else None, publisher=r.get("publisher"))
        if it:
            out.append(it)
    return out


def fetch(src):
    try:
        kind = src["type"]
        if kind == "rss":
            items = parse_rss(src, net.get(src["url"], ua=src.get("ua", "browser")))
        elif kind == "gnews":
            items = parse_gnews(src, net.get(gnews_url(src["query"]), ua=src.get("ua", "browser")))
        elif kind == "telegram":
            url = "https://t.me/s/" + src["channel"]
            items = parse_telegram(src, net.get(url, ua=src.get("ua", "browser")))
        elif kind in ("scrape", "api"):
            items = run_module(src)
        else:
            return {"ok": False, "items": [], "error": "unknown type " + str(kind)}
    except net.FetchError as exc:
        return {"ok": False, "items": [], "error": str(exc)}
    except Exception as exc:  # a parser bug in one source must not cost the pass
        return {"ok": False, "items": [], "error": "{0}: {1}".format(type(exc).__name__, exc)}
    return {"ok": True, "items": items, "error": None}
