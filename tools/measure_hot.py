"""Print what the Hot view shows first, and how old it is.

UX audit tool (2026-10-08): run before and after a ranking change so "fresher" is measured.
    python tools/measure_hot.py [path/to/deals.json] [N]
"""

import json
import sys
from datetime import datetime, timezone

path = sys.argv[1] if len(sys.argv) > 1 else "public/deals.json"
n = int(sys.argv[2]) if len(sys.argv) > 2 else 15
with open(path, encoding="utf-8") as fh:
    doc = json.load(fh)
gen = datetime.fromisoformat(doc["generated_at"].replace("Z", "+00:00"))


def age(s):
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (gen - t).total_seconds() / 86400.0


deals = doc["deals"]
hot = [d for d in deals if "birthday" not in d.get("tags", [])]
print("generated %s  cards %d  hot %d" % (doc["generated_at"], len(deals), len(hot)))
buckets = {"<1d": 0, "1-2d": 0, "2-6d": 0, ">6d": 0}
for d in deals:
    a = age(d["last_seen"])
    buckets["<1d" if a < 1 else "1-2d" if a < 2 else "2-6d" if a < 6 else ">6d"] += 1
print("last_seen age, all cards:", buckets)
top = hot[:12]
print("first page of Hot (12): median first_seen age %.1fd, %d first seen >2d ago"
      % (sorted(age(d["first_seen"]) for d in top)[len(top) // 2],
         sum(age(d["first_seen"]) > 2 for d in top)))
print("%-3s %5s %6s %6s %-14s %s" % ("#", "score", "first", "last", "category", "title"))
for i, d in enumerate(hot[:n], 1):
    print("%-3d %5s %5.1fd %5.1fd %-14s %s" % (i, d["score"], age(d["first_seen"]), age(d["last_seen"]),
                                           d["category"], d["title"][:70]))
