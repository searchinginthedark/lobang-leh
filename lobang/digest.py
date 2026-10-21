"""Morning digest: the 3 best deals first seen in the last 24 hours, pushed once a day.

    python -m lobang.digest [--dry-run] [--now ISO]

Runs as the last step of every collect. Only the first collect inside the send window
(08:00-13:00 SGT) sends; /api/digest holds a per-day lock, so a second collect, a re-run or a
hand dispatch the same day pushes nothing. The top 3 is computed HERE, from the deals.json this
collect just wrote, and POSTed to the endpoint: reading it back from the site would race the
Vercel deploy and digest yesterday's file.

Never fails the job: a digest problem prints and exits 0, because the data commit already landed
and a red collect would hide the real signal (a source outage).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from .textutil import SGT, clip, parse_iso

TOP_N = 3
WINDOW_HOURS = 24
SEND_FROM_HOUR = 8      # SGT; cron-job.org collects at 08:00
SEND_UNTIL_HOUR = 13    # a missed 08:00 collect still sends from the 12:00 one, never in the evening
TITLE_MAX = 70
URL = "https://lobang-leh.vercel.app/api/digest"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pick(deals, now, n=TOP_N):
    """The first n deals (deals.json is already in Hot order) first seen within WINDOW_HOURS.

    Birthday perks are standing offers, not news; an unconfirmed promo may already be over."""
    since = now - timedelta(hours=WINDOW_HOURS)
    out = []
    for d in deals:
        if "birthday" in (d.get("tags") or []) or d.get("unconfirmed"):
            continue
        seen = parse_iso(d.get("first_seen"))
        if seen is None or seen < since:
            continue
        out.append(d)
        if len(out) == n:
            break
    return out


def payload(picked, now):
    """What /api/digest sends. None when there is nothing new: no push beats an empty one."""
    if not picked:
        return None
    n = len(picked)
    return {
        "day": now.astimezone(SGT).date().isoformat(),
        "title": "%d new lobang%s today" % (n, "" if n == 1 else "s"),
        "body": "\n".join("• " + clip(d.get("title") or "", TITLE_MAX) for d in picked),
        "ids": [d["id"] for d in picked],
    }


def in_window(now):
    return SEND_FROM_HOUR <= now.astimezone(SGT).hour < SEND_UNTIL_HOUR


def send(body, secret, url=URL, timeout=30):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + secret})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print the payload, send nothing")
    ap.add_argument("--now", help="pretend it is this ISO time (testing)")
    a = ap.parse_args(argv)
    now = parse_iso(a.now) if a.now else datetime.now(SGT)

    if not a.dry_run and not in_window(now):
        print("digest: outside %02d:00-%02d:00 SGT, nothing to do" % (SEND_FROM_HOUR, SEND_UNTIL_HOUR))
        return 0
    with open(os.path.join(ROOT, "public", "deals.json"), encoding="utf-8") as fh:
        deals = json.load(fh).get("deals") or []
    body = payload(pick(deals, now), now)
    if body is None:
        print("digest: no new deals in the last %d h, nothing sent" % WINDOW_HOURS)
        return 0
    if a.dry_run:
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0
    secret = os.environ.get("DIGEST_SECRET", "")
    if not secret:
        print("digest: DIGEST_SECRET not set, skipped")
        return 0
    try:
        status, text = send(body, secret)
        print("digest: %d %s" % (status, text[:300]))
    except (urllib.error.URLError, OSError) as e:
        print("digest: send failed: %s" % e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
