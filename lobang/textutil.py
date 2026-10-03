"""Text and time helpers shared by sources, classifier and renderer."""

from __future__ import annotations

import calendar
import hashlib
import html
import re
from datetime import datetime, timedelta, timezone

SGT = timezone(timedelta(hours=8))

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
# WordPress appends this to every excerpt; it is boilerplate, not content.
_WP_FOOTER = re.compile(r"\s*The post .{0,300}? appeared first on .{0,120}?\.?\s*$", re.I | re.S)
_READ_MORE = re.compile(r"\s*(\[(…|\.\.\.)\]|Continue reading.*|Read more.*)$", re.I | re.S)


def strip_html(s):
    if not s:
        return ""
    s = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", s)
    s = _TAG.sub(" ", s)
    s = html.unescape(s)
    s = _WP_FOOTER.sub("", s)
    s = _READ_MORE.sub("", s)
    return s.replace(" ", " ").strip()


def one_line(s):
    return _WS.sub(" ", s or "").strip()


def clip(s, n):
    s = one_line(s)
    if len(s) <= n:
        return s
    cut = s[: n - 1]
    sp = cut.rfind(" ")
    if sp > n * 0.6:
        cut = cut[:sp]
    return cut.rstrip(" ,.;:-") + "…"


def sha(s, n=12):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:n]


def now_sgt():
    return datetime.now(SGT).replace(microsecond=0)


def iso(dt):
    return dt.astimezone(SGT).replace(microsecond=0).isoformat() if dt else None


def parse_iso(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=SGT)
    return dt


def from_struct(st):
    """feedparser's *_parsed is a UTC struct_time."""
    if not st:
        return None
    try:
        return datetime.fromtimestamp(calendar.timegm(st), timezone.utc).astimezone(SGT)
    except (OverflowError, ValueError, TypeError):
        return None
