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
# "[…]" / "[...]", or a lone "[" where a feed cut its own marker short (SingPromos, 2026-10-18).
_READ_MORE = re.compile(r"\s*(\[(…|\.\.\.)\]|\[\s*|Continue reading.*|Read more.*)$", re.I | re.S)


def strip_html(s):
    if not s:
        return ""
    s = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", s)
    s = _TAG.sub(" ", s)
    s = html.unescape(s)
    s = _WP_FOOTER.sub("", s)
    s = _READ_MORE.sub("", s)
    return s.replace(" ", " ").strip()


_DROP = re.compile(r"(?is)<(script|style|noscript|iframe|svg|form)\b.*?</\1\s*>|<!--.*?-->")
_BLOCK = re.compile(r"(?i)<br\s*/?>|</?(?:p|div|h[1-6]|li|tr|blockquote|figure|figcaption|section|article|ul|ol|table)\b[^>]*>")
_LI = re.compile(r"(?i)<li\b[^>]*>")
_SPACES = re.compile(r"[ \t\r\f\v ]+")
BODY_MAX = 5000


def body_text(s, n=BODY_MAX):
    """The post's own text for reading in full: paragraphs kept (one per line), boilerplate and
    markup dropped, clipped at a paragraph boundary to `n` chars. Display only: the classifier
    reads `summary`, so a richer body can never change what a post is classified as."""
    if not s:
        return ""
    s = _DROP.sub(" ", s)
    s = _LI.sub("\n• ", s)
    s = _BLOCK.sub("\n", s)
    s = _TAG.sub(" ", s)
    s = html.unescape(s)
    s = _WP_FOOTER.sub("", s)
    s = _READ_MORE.sub("", s)
    lines = []
    for line in s.split("\n"):
        line = _SPACES.sub(" ", line).strip()
        if line and line != "•" and (not lines or line != lines[-1]):
            lines.append(line)
    out, size = [], 0
    for line in lines:
        if size + len(line) > n:
            if not out:
                out.append(clip(line, n))
            else:
                out.append("…")
            break
        out.append(line)
        size += len(line) + 1
    return "\n".join(out)


def tidy_tail(s):
    """Drop a trailing read-more marker from text stored before strip_html learned it."""
    return _READ_MORE.sub("", s or "")


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
