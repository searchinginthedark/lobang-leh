"""Cluster classified items into deals, aggregate them, and score them.

Everything here is a pure function of its inputs (plus `today`), so a rebuild from
data/items.jsonl reproduces the same deals.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date

from .classify import fold
from .textutil import clip, parse_iso, sha

TIER_RANK = {"deals": 0, "media": 1, "news": 2, "social": 3}
STRONG = ("1-for-1", "free", "pct-off", "cheap")

_STOP = set("""
a an the and or of for to in on at by with from via your our you we is are be this that these those it its
sg singapore deal deals promo promos promotion promotions offer offers off free only just now new get
till until til ends end valid from today this weekend week day days daily all more lobang lobangs
jan feb mar apr may jun jul aug sep sept oct nov dec january february march april june july august
september october november december mon tue wed thu fri sat sun monday tuesday wednesday thursday friday
saturday sunday 2025 2026 2027 here what where how why when best top 1 2 3 one two
""".split())
_TOKEN = re.compile(r"[a-z0-9&']+")
_GENERIC = set("""
open opens opening opened first outlet outlets store stores shop branch restaurant restaurants cafe cafes
chain brand viral famous popular hit coming arrives lands debut debuts launch launches review our honest
food drinks drink menu bakery new latest check out visit try must at mall s'pore lands landed spot spots
overseas international outpost
""".split())

PROMO_STALE_DAYS = 14     # no stated end date: assume a promo has lapsed after two weeks
OPENING_STALE_DAYS = 30
STATE_KEEP_DAYS = 45      # how long a deal stays matchable after its last new item


def norm_publisher(p):
    p = fold(p or "")
    p = re.sub(r"^(www\.)|\.(com|sg|net|org|co)(\.sg)?$", "", p)
    return re.sub(r"[^a-z0-9]", "", p)


def tokens(title, merchants=()):
    t = fold(title)
    for m in merchants:
        t = t.replace(fold(m), " ")
    words = (w[:-2] if w.endswith("'s") else w.strip("'") for w in _TOKEN.findall(t))
    return {w for w in words if w and w not in _STOP and not (w.isdigit() and len(w) <= 2)}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def _days(a, b):
    return abs((a - b).total_seconds()) / 86400.0


def _when(member):
    return parse_iso(member.get("published")) or parse_iso(member["fetched"])


def match_score(item, deal):
    """>0 when the item belongs to this deal (higher = better), else 0."""
    c = item["cls"]
    if c["kind"] != deal["kind"]:
        return 0.0
    when = _when(item)
    last = max(_when(m) for m in deal["members"])
    gap = _days(when, last)
    im = set(c["merchants"])
    dm = set(deal["merchants"])
    it = tokens(item["title"], c["merchants"])
    dt = set()
    for m in deal["members"]:
        dt |= tokens(m["title"], m["cls"]["merchants"])
    sim = jaccard(it, dt)
    if im and dm:
        if not (im & dm):
            return 0.0
        if c["kind"] == "opening":
            return 1.0 + sim if gap <= 30 else 0.0
        if gap > 10:
            return 0.0
        du = deal.get("valid_until")
        iu = c.get("valid_until")
        if du and iu and abs((date.fromisoformat(du) - date.fromisoformat(iu)).days) > 2:
            return 0.0   # same chain, different promo period
        shared_strong = set(c["tags"]) & set(deal["tags"]) & set(STRONG)
        # Same chain + same deal type: merge when the end dates agree, or when one side
        # has none but the posts are within 3 days (a Telegram "Sushiro 1-for-1" post
        # beside a blog's dated write-up of the same promo).
        if sim >= 0.25 or (shared_strong and ((du and iu) or gap <= 3)):
            return 0.5 + sim
        return 0.0
    if im or dm:
        return 0.0
    # No lexicon merchant on either side (an unknown brand). Five outlets wrote up
    # "I'm donut?" five ways, so Jaccard alone never reached 0.5; overlap on the
    # distinctive words (generic opening vocabulary removed) does.
    a, b = it - _GENERIC, dt - _GENERIC
    shared = a & b
    overlap = len(shared) / float(min(len(a), len(b))) if a and b else 0.0
    window = 30 if c["kind"] == "opening" else 5
    if gap <= window and (sim >= 0.5 or (len(shared) >= 2 and overlap >= 0.6)):
        return max(sim, overlap) * 0.9
    return 0.0


def assign(new_items, deals):
    """Attach each new classified item to its best deal or open a new one. Mutates `deals`."""
    for item in sorted(new_items, key=lambda i: (i.get("published") or i["fetched"], i["id"])):
        best, best_s = None, 0.0
        for d in deals:
            s = match_score(item, d)
            if s > best_s:
                best, best_s = d, s
        if best is None:
            best = {"id": "d_" + sha(item["id"], 10), "members": []}
            deals.append(best)
        best["members"].append(item)
        aggregate(best)
    return deals


def _mode_latest(values):
    vals = [v for v in values if v]
    if not vals:
        return None
    cnt = Counter(vals)
    top = max(cnt.values())
    return max(v for v in cnt if cnt[v] == top)


def aggregate(deal):
    ms = deal["members"]
    kinds = Counter(m["cls"]["kind"] for m in ms)
    deal["kind"] = "promo" if kinds["promo"] >= kinds["opening"] else "opening"
    order = sorted(ms, key=lambda m: (TIER_RANK.get(m["tier"], 9), m.get("published") or m["fetched"]))
    lead = order[0]
    deal["title"] = lead["title"]
    summaries = [m["summary"] for m in order if m.get("summary")]
    deal["summary"] = clip(summaries[0], 280) if summaries else ""

    mcount = Counter()
    first = {}
    for i, m in enumerate(ms):
        for n in m["cls"]["merchants"]:
            mcount[n] += 1
            first.setdefault(n, i)
    deal["merchants"] = sorted(mcount, key=lambda n: (-mcount[n], first[n]))[:3]

    tags = []
    for m in order:
        for t in m["cls"]["tags"]:
            if t not in tags:
                tags.append(t)
    deal["tags"] = tags
    pcts = [m["cls"]["pct"] for m in ms if m["cls"].get("pct")]
    deal["pct"] = max(pcts) if pcts else None
    deal["valid_until"] = _mode_latest(m["cls"].get("valid_until") for m in ms)
    froms = [m["cls"]["valid_from"] for m in ms if m["cls"].get("valid_from")]
    deal["valid_from"] = min(froms) if froms else None
    cats = Counter(m["cls"]["category"] for m in order if m["cls"]["category"] != "other")
    deal["category"] = cats.most_common(1)[0][0] if cats else "other"
    origins = [m["cls"]["origin"] for m in order if m["cls"].get("origin")]
    deal["origin"] = origins[0] if origins else None
    deal["famous"] = any(m["cls"].get("famous") for m in ms)

    pubs = {}
    for m in sorted(ms, key=lambda m: m.get("published") or m["fetched"], reverse=True):
        key = norm_publisher(m["publisher"])
        if key not in pubs:
            pubs[key] = {"publisher": m["publisher"], "url": m["url"], "title": m["title"]}
    deal["links"] = list(pubs.values())[:6]
    deal["publishers"] = len(pubs)
    deal["best_tier"] = lead["tier"]
    deal["published"] = min((m.get("published") or m["fetched"]) for m in ms)
    deal["first_seen"] = min(m["fetched"] for m in ms)
    deal["last_seen"] = max(m["fetched"] for m in ms)
    return deal


def score(deal, today):
    """0-100. Deterministic for a given deal and date."""
    tags = set(deal["tags"])
    s = 30.0
    strength = []
    if "1-for-1" in tags:
        strength.append(25)
    if "free" in tags:
        strength.append(20)
    if deal.get("pct"):
        strength.append(20 if deal["pct"] >= 50 else 12 if deal["pct"] >= 30 else 6)
    if "cheap" in tags:
        strength.append(12)
    if "bundle" in tags:
        strength.append(5)
    if strength:
        strength.sort(reverse=True)
        s += min(30, strength[0] + 5 * (len(strength) - 1))
    if deal["kind"] == "opening":
        s += 20 if "first-in-sg" in tags else 0
        # A foreign chain's 10th SG outlet is routine; its first one is the news.
        s += (15 if "first-in-sg" in tags else 5) if deal.get("origin") else 0
        s += 10 if deal.get("famous") else 0
    elif deal.get("famous"):
        s += 8
    n = deal["publishers"]
    s += 14 if n >= 3 else 8 if n == 2 else 0
    s += {"deals": 4, "media": 4, "news": 2}.get(deal.get("best_tier"), 0)
    if not deal["merchants"]:
        s -= 8
    if "card" in tags:
        s -= 5
    until = deal.get("valid_until")
    if until:
        left = (date.fromisoformat(until) - today).days
        if 0 <= left <= 1:
            s += 6
    pub = parse_iso(deal["published"]).date()
    age = (today - pub).days
    penalty = min(20, max(0, age - 2) * 2)
    if until and date.fromisoformat(until) >= today:
        penalty /= 2.0   # a deal with a stated, unexpired end date is still live
    s -= penalty
    return int(max(0, min(100, round(s))))


def is_live(deal, today):
    until = deal.get("valid_until")
    if until:
        return date.fromisoformat(until) >= today
    pub = parse_iso(deal["published"]).date()
    stale = OPENING_STALE_DAYS if deal["kind"] == "opening" else PROMO_STALE_DAYS
    return (today - pub).days <= stale


def public(deal, today):
    tags = [t for t in deal["tags"]]
    if deal.get("valid_until") == today.isoformat() and "ends-today" not in tags:
        tags.append("ends-today")
    out = {
        "id": deal["id"],
        "kind": deal["kind"],
        "title": deal["title"],
        "merchants": deal["merchants"],
        "category": deal["category"],
        "tags": tags,
        "origin": deal.get("origin"),
        "valid_from": deal.get("valid_from"),
        "valid_until": deal.get("valid_until"),
        "published": deal["published"],
        "first_seen": deal["first_seen"],
        "last_seen": deal["last_seen"],
        "score": score(deal, today),
        "summary": deal["summary"],
        "publishers": deal["publishers"],
        "links": deal["links"],
    }
    if deal.get("pct"):
        out["pct"] = deal["pct"]
    return out
