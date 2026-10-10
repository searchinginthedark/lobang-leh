"""Where a deal is, read from the post's own words (config/places.yml). No geocoding, no guessing:
a post that names no place gets no place, and a chain-wide promo stays placeless.

Places.find(folded_text) ->[{"name", "mrt", "region"}], at most 3, in text order.
"""

from __future__ import annotations

import re

import yaml

from .classify import fold

REGIONS = ("Central", "East", "North", "North-East", "West")
# A chain-wide deal names places only to exclude them ("all outlets except Changi Airport",
# "islandwide, excluding T1, T2 & T3"), so a text that says so gives no place at all.
EVERYWHERE = re.compile(r"(?<![\w])(?:island-?wide|all (?:its |our |participating |\d+ )?(?:outlets|stores|branches|"
                        r"restaurants|locations)|every \w+ (?:outlet|store))(?![\w])")
# Long excerpts are review or deal-site prose that names outlets to compare or exclude ("the
# exclusive drinks at Starbucks WEAVE in Resorts World Sentosa are out"); 12 of 55 excerpt places
# were wrong that way (2026-10-11). Short ones, or ones with a unit number or a LOCATION: label,
# are a deal channel saying where.
EXCERPT_MAX = 240
WHERE_MARK = re.compile(r"#\s?b?\d{1,2}-[a-z]?\d|(?<![\w])location:")   # #01-36, #B1-K05
# A qualified station name only counts with one of these after it ("Expo" alone is any expo).
_STATION = r"(?:\s+(?:mrt(?:\s+station)?|station|interchange))"


def merge(found, cap=3):
    """Distinct places in order, at most cap. "VivoCity, near HarbourFront MRT" (or one post saying
    Great World City and another Great World) is one place: a bare station some mall already
    names is dropped."""
    out = []
    for e in found:
        if e["name"] not in [o["name"] for o in out]:
            out.append(e)
    malls = {e["mrt"] for e in out if e.get("mrt") and e["mrt"] != e["name"]}
    out = [e for e in out if not (e.get("mrt") == e["name"] and e["name"] in malls)]
    return [dict(e) for e in out[:cap]]


class Places(object):
    def __init__(self, cfg):
        region_of = {}
        for region, names in (cfg.get("stations") or {}).items():
            if region not in REGIONS:
                raise ValueError("places.yml: unknown region %r" % region)
            for n in names:
                region_of[n] = region
        qualified = set(cfg.get("qualified") or [])
        unknown = qualified - set(region_of)
        if unknown:
            raise ValueError("places.yml: qualified names that are not stations: %s" % sorted(unknown))

        pats = []
        for n, region in region_of.items():
            body = re.escape(fold(n)) + (_STATION if n in qualified else _STATION + "?")
            pats.append((len(n), body, {"name": n, "mrt": n, "region": region}))
        for p in cfg.get("places") or []:
            mrt = p.get("mrt")
            if mrt and mrt not in region_of:
                raise ValueError("places.yml: %s names unknown station %r" % (p["name"], mrt))
            region = region_of[mrt] if mrt else p.get("region")
            if region not in REGIONS:
                raise ValueError("places.yml: %s needs an mrt or a region" % p["name"])
            entry = {"name": p["name"], "mrt": mrt, "region": region}
            for alias in [p["name"]] + list(p.get("aliases") or []):
                a = fold(alias).strip()
                pats.append((len(a), re.escape(a).replace("'", "'?"), entry))
        # Longest first, so "Tampines West" beats "Tampines" and "Jurong Point" beats "Jurong".
        pats.sort(key=lambda p: -p[0])
        self._entries = [p[2] for p in pats]
        self._rx = re.compile("|".join(r"(?<![\w])({0})(?![\w])".format(p[1]) for p in pats))
        ign = [re.escape(fold(s)) for s in cfg.get("ignore") or []]
        self._ignore = re.compile(r"(?<![\w])(?:" + "|".join(ign) + r")(?![\w])") if ign else None

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as fh:
            return cls(yaml.safe_load(fh) or {})

    def find(self, folded):
        """folded: text already passed through classify.fold. Phrases in `ignore` (a brand or dish
        named after a place, "Tiong Bahru Bakery") are blanked first."""
        t = folded
        if self._ignore is not None:
            t = self._ignore.sub(lambda m: " " * len(m.group(0)), t)
        return merge([self._entries[m.lastindex - 1] for m in self._rx.finditer(t)])

    def locate(self, title, summary):
        """Places for one post (both args folded): the headline's, else a trustworthy excerpt's."""
        if EVERYWHERE.search(title):
            return []
        found = self.find(title)
        if found or not summary or EVERYWHERE.search(summary):
            return found
        if len(summary) > EXCERPT_MAX and not WHERE_MARK.search(summary):
            return []
        found = self.find(summary)
        # Three or more in an excerpt is an outlet list for a chain-wide deal, not where it is.
        return found if len(found) < 3 else []
