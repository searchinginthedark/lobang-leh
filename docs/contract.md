# Data contract: `public/deals.json`

Written by the collector (`python -m lobang.fetch`), read by the static page in `public/`.
The page never fetches anything else except `./deals.json`. Nothing in this file is
LLM-generated: every title, summary and link comes from a fetched source.

```json
{
  "schema": 1,
  "generated_at": "2026-10-03T09:15:00+08:00",
  "window_days": 21,
  "health": {
    "ok": 14, "total": 16,
    "sources": [
      {"name": "singpromos", "publisher": "SingPromos", "type": "rss",
       "ok": true, "count": 30, "fnb": 18, "error": null,
       "last_ok": "2026-10-03T09:14:58+08:00"}
    ]
  },
  "deals": [
    {
      "id": "d_3f9a1c2b7e",
      "kind": "promo",
      "title": "McDonald's 1-for-1 McSpicy via app till 12 Oct",
      "merchants": ["McDonald's"],
      "category": "fast-food",
      "tags": ["1-for-1", "app-only"],
      "origin": null,
      "valid_from": "2026-10-03",
      "valid_until": "2026-10-12",
      "published": "2026-10-03T08:00:00+08:00",
      "first_seen": "2026-10-03T09:14:58+08:00",
      "last_seen": "2026-10-03T09:14:58+08:00",
      "score": 72,
      "summary": "Plain text from the source, at most 280 chars.",
      "publishers": 2,
      "links": [
        {"publisher": "SingPromos", "url": "https://...", "title": "..."}
      ]
    }
  ]
}
```

## Field rules
- `kind`: `"promo"` (a price deal) or `"opening"` (a new outlet / brand launch in SG).
- `category`: one of `fast-food`, `coffee`, `bubble-tea`, `bakery-dessert`, `buffet`,
  `restaurant`, `cafe`, `bar-drinks`, `hawker`, `grocery`, `delivery`, `other`.
- `tags`: zero or more of `1-for-1`, `pct-off`, `free`, `cheap` (a stated price <= $5),
  `bundle`, `app-only`, `card`, `member`, `delivery`, `buffet`, `overseas`, `first-in-sg`,
  `limited`, `ends-today`. Unknown tags must be ignored by the page, never crash it.
  `pct-off` deals also carry `"pct": 50` (an int) on the deal object.
- `birthday` tag: a CUSTOMER birthday perk (free cake in your birthday month). A brand's own
  birthday ("turns 35", "founder's birthday", "Birthday Bash") is an ordinary promo without it.
  Tagged deals also carry a `birthday` object (see below). Birthday perks are standing offers,
  so `valid_until` is usually `null`.
- `origin`: country name for an overseas brand (`"Japan"`, `"Korea"`, ...) or `null`.
- `valid_from` / `valid_until`: `YYYY-MM-DD` (Singapore date) or `null` when the source
  does not state it. `null` means UNKNOWN, never "no expiry".
- Times are ISO-8601 with `+08:00`.
- `deals` is pre-sorted for the Hot view: `score` minus 8 points per day since `last_seen`
  (12 hours' grace), highest first (`deals.hot_rank`). `score` itself is 0-100, deterministic,
  and does not include that decay.
- `links` holds at most 6 entries, newest first; `publishers` is the full distinct count.
- Expired deals (`valid_until` before today SGT) are already removed by the collector.
- `health.ok == 0` never reaches this file: the collector refuses to write it.

## `birthday` (only on deals tagged `birthday`)

```json
"birthday": {"window": "around", "before": 14, "after": 14, "days": null, "excl_ph": false,
             "needs": ["member", "min-spend"], "min_spend": 200, "group": null,
             "signup_days": 14, "said": "14 days before & after birthday."}
```

- `window`, relative to the viewer's birthday B (month M):
  - `day`: B only. `around`: B - `before` days to B + `after` days.
  - `month`: the whole of month M. `month-plus`: from the 1st of M for `after` days.
  - `week`: "birthday week" as stated; not resolvable to dates, show the wording.
  - `visit`: "day of dining in", i.e. tell staff on the day you dine; no date rule stated.
  - `unknown`: the source states no window. Never read it as "month".
- `days`: weekday restriction as stated (`"Mon-Thu"`, `"Weekdays"`, `"Weekends"`) or `null`.
- `excl_ph`: public holidays are excluded.
- `needs`: zero or more of `member`, `app`, `min-spend`, `group`, `booking`, `id`, `prior-purchase`.
- `min_spend` (S$), `group` (party size including the birthday person), `signup_days` (join at
  least this many days ahead): ints or `null`.
- `said`: the source's own wording for the window, at most 160 chars, or `null`. Show it: other
  roundups disagree on the same brand, and blackout dates live only here.
