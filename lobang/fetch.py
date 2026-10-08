"""Collect -> classify -> cluster -> score -> write.

    python -m lobang.fetch [--dry-run] [--only NAME] [--json]

Exit codes: 0 written, 2 every source failed (nothing written: a total outage is
never published as "no deals").
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import yaml

from . import deals as D
from .classify import Lexicon, classify
from .sources import fetch
from .textutil import iso, now_sgt, parse_iso

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "config")
DATA = os.path.join(ROOT, "data")
PUBLIC = os.path.join(ROOT, "public")
ITEMS = os.path.join(DATA, "items.jsonl")
STATE = os.path.join(DATA, "state.json")
DEALS = os.path.join(DATA, "deals.json")

ITEM_MAX_AGE_DAYS = 21     # older items are ignored at ingest
LEDGER_DAYS = 30           # items.jsonl window; older lines are gzipped to data/archive/


def load_json(path, default):
    try:
        with io.open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default


def write_json(path, obj, lines_key=None):
    """Atomic write. With lines_key, one list element per line so git diffs stay small."""
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        if lines_key:
            head = {k: v for k, v in obj.items() if k != lines_key}
            fh.write("{\n")
            for k, v in head.items():
                fh.write("  {0}: {1},\n".format(json.dumps(k), json.dumps(v, ensure_ascii=False)))
            fh.write("  {0}: [\n".format(json.dumps(lines_key)))
            rows = obj[lines_key]
            for i, r in enumerate(rows):
                fh.write("    " + json.dumps(r, ensure_ascii=False, sort_keys=True))
                fh.write(",\n" if i < len(rows) - 1 else "\n")
            fh.write("  ]\n}\n")
        else:
            json.dump(obj, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write("\n")
    os.replace(tmp, path)


def load_sources(only=None):
    with io.open(os.path.join(CFG, "sources.yml"), encoding="utf-8") as fh:
        srcs = (yaml.safe_load(fh) or {}).get("sources") or []
    srcs = [s for s in srcs if not s.get("disabled")]
    # A free-key source with no key set is OFF, not failing: it must not drag ok/total down
    # on a laptop without .env, nor fake an outage. Named on stderr so it is never silent.
    nokey = [s["name"] for s in srcs if s.get("env") and not os.environ.get(s["env"])]
    if nokey:
        print("skipped (no key): " + ", ".join(nokey), file=sys.stderr)
    srcs = [s for s in srcs if s["name"] not in nokey]
    if only:
        srcs = [s for s in srcs if s["name"] == only]
    return srcs


def read_ledger():
    rows = []
    if os.path.exists(ITEMS):
        with io.open(ITEMS, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def rotate_ledger(rows, now):
    """Keep LEDGER_DAYS in items.jsonl; append older rows to a monthly gzip archive."""
    cutoff = now - timedelta(days=LEDGER_DAYS)
    keep, old = [], []
    for r in rows:
        (old if parse_iso(r["fetched"]) < cutoff else keep).append(r)
    if old:
        os.makedirs(os.path.join(DATA, "archive"), exist_ok=True)
        by_month = {}
        for r in old:
            by_month.setdefault(r["fetched"][:7], []).append(r)
        for month, rs in sorted(by_month.items()):
            path = os.path.join(DATA, "archive", "items-{0}.jsonl.gz".format(month))
            with gzip.open(path, "at", encoding="utf-8", newline="\n") as fh:
                for r in rs:
                    fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    return keep


def source_flags(m, by_name):
    """A stored item with its source's CURRENT config flags, ready for classify().

    The flags live in config, not the ledger, so a config change reaches stored items too.
    Shared with tools/replay.py so the replay classifies exactly what the collector does."""
    it = dict(m)
    src = by_name.get(m.get("source"))
    if src:
        it["fnb_only"] = bool(src.get("fnb_only"))
        it["birthday_only"] = bool(src.get("birthday_only"))
        it["post_body"] = src.get("type") == "telegram"
    return it


def run(dry_run=False, only=None, as_json=False):
    now = now_sgt()
    today = now.date()
    lex = Lexicon.load(os.path.join(CFG, "merchants.yml"))
    sources = load_sources(only)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(fetch, sources))   # map keeps config order: deterministic

    prev = {s["name"]: s for s in load_json(STATE, {}).get("sources", [])}
    health = []
    ok_count = 0
    ledger = read_ledger()
    state = load_json(DEALS, {"deals": []})
    deal_list = state["deals"]
    # Deal members count as seen too: a standing offer outlives the 30-day ledger window,
    # and must not be re-ingested as "new" the day its ledger line rotates out.
    seen = {r["id"] for r in ledger} | {m["id"] for d in deal_list for m in d["members"]}
    listed = set()   # ids a `standing: true` source still lists this run
    fresh = []
    min_pub = now - timedelta(days=ITEM_MAX_AGE_DAYS)
    for src, res in zip(sources, results):
        fnb = 0
        if res["ok"]:
            ok_count += 1
        for it in res["items"]:
            if src.get("standing"):
                listed.add(it["id"])
            pub = it["published"]
            if pub and pub < min_pub:
                continue
            ref = (pub or now).date()
            cls = classify(it, lex, ref)
            if cls:
                fnb += 1
            if it["id"] in seen:
                continue
            seen.add(it["id"])
            row = dict(it)
            row["published"] = iso(pub)
            row["fetched"] = iso(now)
            row["cls"] = cls
            fresh.append(row)
        p = prev.get(src["name"], {})
        health.append({
            "name": src["name"], "publisher": src.get("publisher", src["name"]), "type": src["type"],
            "ok": res["ok"], "count": len(res["items"]), "fnb": fnb, "error": res["error"],
            "last_ok": iso(now) if res["ok"] else p.get("last_ok"),
        })

    if ok_count == 0:
        print("ERROR: all {0} sources failed; refusing to write".format(len(sources)), file=sys.stderr)
        for h in health:
            print("  {0}: {1}".format(h["name"], h["error"]), file=sys.stderr)
        return 2

    # Re-check stored members against today's rules and config (after `seen`, so a member
    # dropped here is not re-ingested next run).
    by_name = {s["name"]: s for s in sources}

    def still_fnb(m):
        it = source_flags(m, by_name)
        when = parse_iso(m.get("published")) or parse_iso(m["fetched"])
        return classify(it, lex, when.date()) is not None

    deal_list = D.prune(deal_list, still_fnb)
    D.assign([r for r in fresh if r["cls"]], deal_list)
    for d in deal_list:
        if any(m["id"] in listed for m in d["members"]):
            d["last_listed"] = iso(now)
    keep_after = now - timedelta(days=D.STATE_KEEP_DAYS)
    deal_list = [d for d in deal_list
                 if parse_iso(d.get("last_listed") or d["last_seen"]) >= keep_after
                 or parse_iso(d["last_seen"]) >= keep_after]

    live = [D.public(d, today) for d in deal_list if D.is_live(d, today)]
    D.hot_sort(live, now)
    out = {
        "schema": 1,
        "generated_at": iso(now),
        "window_days": ITEM_MAX_AGE_DAYS,
        "health": {"ok": ok_count, "total": len(sources), "sources": health},
        "deals": live,
    }

    summary = "{0}/{1} sources ok, {2} new items ({3} F&B), {4} live deals ({5} promo, {6} opening)".format(
        ok_count, len(sources), len(fresh), sum(1 for r in fresh if r["cls"]), len(live),
        sum(1 for d in live if d["kind"] == "promo"), sum(1 for d in live if d["kind"] == "opening"))
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print(summary)
        for h in health:
            print("  {0:<24} {1:<4} items={2:<3} fnb={3:<3} {4}".format(
                h["name"], "ok" if h["ok"] else "FAIL", h["count"], h["fnb"], h["error"] or ""))
    if dry_run:
        return 0

    os.makedirs(DATA, exist_ok=True)
    ledger = rotate_ledger(ledger + fresh, now)
    tmp = ITEMS + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        for r in ledger:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, ITEMS)
    write_json(DEALS, {"deals": deal_list}, lines_key="deals")
    write_json(STATE, {"updated": iso(now), "sources": health})
    os.makedirs(PUBLIC, exist_ok=True)
    write_json(os.path.join(PUBLIC, "deals.json"), out, lines_key="deals")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lobang.fetch")
    ap.add_argument("--dry-run", action="store_true", help="fetch and classify, write nothing")
    ap.add_argument("--only", help="one source by name")
    ap.add_argument("--json", action="store_true", help="print the public JSON")
    a = ap.parse_args(argv)
    return run(dry_run=a.dry_run, only=a.only, as_json=a.json)


if __name__ == "__main__":
    sys.exit(main())
