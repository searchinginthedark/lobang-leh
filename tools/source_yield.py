"""What each source actually contributes, over the 30-day ledger, under today's rules.

    python tools/source_yield.py

`fnb` in data/state.json counts only the items in a feed's CURRENT window (its latest 10-40 posts),
so a slow-but-useful source reads 0 on a quiet day (2026-10-08: thesmartlocal and straitstimes_life
both read 0 while being the only source of 3 live cards). Judge a source by this report instead:
items seen and classified over 30 days, and how many live cards rest on it alone.
"""

import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lobang import fetch as F  # noqa: E402
from lobang.classify import Lexicon, classify  # noqa: E402
from lobang.textutil import parse_iso  # noqa: E402


def main():
    sources = F.load_sources()
    by_name = {s["name"]: s for s in sources}
    lex = Lexicon.load(os.path.join(ROOT, "config", "merchants.yml"))
    items, fnb = Counter(), Counter()
    with open(os.path.join(ROOT, "data", "items.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            m = json.loads(line)
            if m.get("source") not in by_name:
                continue
            items[m["source"]] += 1
            when = parse_iso(m.get("published")) or parse_iso(m["fetched"])
            if classify(F.source_flags(m, by_name), lex, when.date()):
                fnb[m["source"]] += 1
    with open(os.path.join(ROOT, "data", "deals.json"), encoding="utf-8") as fh:
        deals = json.load(fh)["deals"]
    sole, any_ = Counter(), Counter()
    for d in deals:
        srcs = {m["source"] for m in d["members"]}
        for s in srcs:
            any_[s] += 1
        if len(srcs) == 1:
            sole[next(iter(srcs))] += 1
    print("%-24s %6s %6s %6s %6s" % ("source (30-day ledger)", "items", "fnb", "cards", "sole"))
    for s in sorted(by_name, key=lambda n: (fnb[n], sole[n])):
        flag = "  <-- nothing in 30 days" if fnb[s] == 0 and any_[s] == 0 else ""
        print("%-24s %6d %6d %6d %6d%s" % (s, items[s], fnb[s], any_[s], sole[s], flag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
