"""Blast radius of a classifier change: every stored headline, old rules vs new.

    python tools/replay.py [--base REV]      (default base: HEAD)

Classifies every item in data/items.jsonl plus every stored deal member twice, once with the
rules in the working tree and once with the rules at REV (extracted with `git archive`, never
checked out), and prints each headline whose outcome differs: DROPPED, ADDED, KIND (promo vs
opening), TAGS (kind unchanged, tags differ), PLACES (only the place line differs) or DATES (only
valid_from/valid_until differ: the card's "Till" line and when it expires). Exit 0 always; read the list. Run it before committing any change to lobang/classify.py,
lobang/birthday.py, lobang/places.py, config/merchants.yml, config/places.yml or config/sources.yml, and put every surprise into
tests/fixtures/headlines.tsv.
"""

import argparse
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_items():
    items = {}
    with open(os.path.join(ROOT, "data", "items.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            items[r["id"]] = r
    with open(os.path.join(ROOT, "data", "deals.json"), encoding="utf-8") as fh:
        for d in json.load(fh).get("deals", []):
            for m in d["members"]:
                items.setdefault(m["id"], m)
    return list(items.values())


def classify_all(root, items):
    """{id: (kind | None, tags)} using the lobang package and config found under root."""
    sys.path.insert(0, root)
    try:
        import yaml
        from lobang import fetch
        from lobang.classify import Lexicon, classify
        from lobang.textutil import parse_iso
        lex = Lexicon.load(os.path.join(root, "config", "merchants.yml"))
        with open(os.path.join(root, "config", "sources.yml"), encoding="utf-8") as fh:
            by_name = {s["name"]: s for s in yaml.safe_load(fh)["sources"]}
        flags = getattr(fetch, "source_flags", None)
        out = {}
        for m in items:
            it = flags(m, by_name) if flags else dict(m)
            if not flags and m.get("source") in by_name:
                it["fnb_only"] = bool(by_name[m["source"]].get("fnb_only"))
                it["birthday_only"] = bool(by_name[m["source"]].get("birthday_only"))
            when = parse_iso(m.get("published")) or parse_iso(m["fetched"])
            c = classify(it, lex, when.date())
            out[m["id"]] = ((c["kind"], sorted(c["tags"]), [p["name"] for p in c.get("places") or []],
                             [c.get("valid_from"), c.get("valid_until")])
                            if c else (None, [], [], [None, None]))
        return out
    finally:
        sys.path.remove(root)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="HEAD")
    ap.add_argument("--dump", help=argparse.SUPPRESS)   # internal: classify with rules under this root
    a = ap.parse_args(argv)
    items = load_items()
    if a.dump:
        json.dump(classify_all(a.dump, items), sys.stdout)
        return 0

    new = classify_all(ROOT, items)
    with tempfile.TemporaryDirectory() as tmp:
        tar = subprocess.run(["git", "-C", ROOT, "archive", a.base, "lobang", "config"],
                             check=True, capture_output=True).stdout
        tarfile.open(fileobj=io.BytesIO(tar)).extractall(tmp)
        # A separate process: both rule sets are the package `lobang`, so they cannot share one.
        res = subprocess.run([sys.executable, os.path.abspath(__file__), "--dump", tmp],
                             check=True, capture_output=True)
        old = {k: tuple(v) for k, v in json.loads(res.stdout.decode("utf-8")).items()}

    by_id = {m["id"]: m for m in items}
    rows = []
    for i, (nk, ntags, nplaces, ndates) in new.items():
        ok, otags, oplaces, odates = old.get(i, (None, [], [], [None, None]))
        same = ok == nk and list(otags) == list(ntags)
        if same and list(oplaces) == list(nplaces) and list(odates) == list(ndates):
            continue
        if same and list(oplaces) == list(nplaces):
            what = "DATES %s..%s" % (ndates[0] or "?", ndates[1] or "?")
        elif same:
            # The card's place line (config/places.yml) is user-visible as well.
            what = "PLACES %s" % (" / ".join(nplaces) or "none")
        elif ok == nk:
            # Tags are user-visible too ("Under $5", "1-for-1"), so a tag-only change is reported.
            gone = sorted(set(otags) - set(ntags))
            came = sorted(set(ntags) - set(otags))
            what = "TAGS" + "".join(" -" + t for t in gone) + "".join(" +" + t for t in came)
        else:
            what = "DROPPED" if nk is None else "ADDED" if ok is None else "KIND %s>%s" % (ok, nk)
        m = by_id[i]
        rows.append((what, m.get("source", "?"), m["title"]))
    seen = set()
    rows = [r for r in sorted(rows) if not (r[2] in seen or seen.add(r[2]))]
    print("replay %s -> working tree: %d items, %d headlines change" % (a.base, len(items), len(rows)))
    for what, src, title in rows:
        print("  %-18s %-22s %s" % (what, src, title[:100]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
