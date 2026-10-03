# LobangLeh

Singapore F&B promotions and new openings (especially overseas brands landing in SG),
collected from 29 free sources. No API keys. Nothing is written or summarised by a
language model: every card is a fetched headline with its publishers and links.

## How it works

```
config/sources.yml   13 RSS feeds, 12 Google News queries, 4 public Telegram channels
config/merchants.yml ~320 SG F&B brands: aliases, category, origin country, famous
lobang/sources.py    fetch + parse; a failure is {ok:false}, never an empty list
lobang/classify.py   keyword rules: F&B? SG? promo or opening? tags, end date, merchant
lobang/deals.py      cluster the same deal across publishers, aggregate, score 0-100
lobang/fetch.py      CLI: writes data/ (ledger) and public/deals.json (the page's data)
public/              static PWA, reads ./deals.json only
```

```bash
pip install -r requirements.txt
python -m lobang.fetch --dry-run     # fetch + classify, write nothing, print source health
python -m lobang.fetch               # write data/ and public/deals.json
python -m unittest discover -s tests
python tools/probe_sources.py        # one line per source: status, items, UA
```

Exit code 2 means every source failed; nothing is written, so an outage never
publishes "no deals".

## Scoring

Base 30, plus the strongest deal type (1-for-1 +25, free +20, 50%+ off +20, under $5 +12),
+5 for each extra type (deal-type total capped at +30), corroboration (+8 for 2 publishers,
+14 for 3+), +8 for a famous chain, +4 when a deal site or food publisher carries it (+2 news),
+6 when it ends today or tomorrow. Openings: +20 first in SG, +15 overseas brand (+5 if not
its first outlet), +10 famous. Penalties: unknown merchant -8, card-only -5, age -2/day after
day 2 (capped at -20, halved while a stated end date is still ahead).

A deal with no stated end date drops off after 14 days (openings 30); one with an end date
drops off the day after it.

## Scheduling

`.github/workflows/collect.yml` runs at 08:00, 12:00, 17:00 and 21:00 SGT and commits the
data back; every push redeploys on Vercel. GitHub drops many scheduled triggers, so for
reliable runs point an external cron (cron-job.org) at:

```
POST https://api.github.com/repos/Zhiyang123/lobang-leh/actions/workflows/collect.yml/dispatches
Authorization: Bearer <fine-grained PAT, this repo only: Actions read+write, Contents read>
Accept: application/vnd.github+json
{"ref":"main","inputs":{"source":"cron-job.org"}}
```

Success is `204 No Content`. The run list shows `collect (cron-job.org)` for those runs.
