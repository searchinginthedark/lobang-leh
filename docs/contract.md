# Data contract: `public/deals.json`

Written by the collector (`python -m lobang.fetch`), read by the static page in `public/`.
The page fetches `./deals.json` on every open; `./details.json`, `./vectors.json` and the search
model in `./embed/` only on demand (see below). Nothing in these files is
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
- `places` (optional, absent when the posts name no place): at most 3
  `{"name": "Hougang Mall", "mrt": "Hougang", "region": "North-East"}`, from `config/places.yml`.
  `name` is the mall, food centre, station or neighbourhood the post names; `mrt` the nearest MRT
  station or `null` (Joo Chiat, Sentosa); `region` one of `Central`, `East`, `North`, `North-East`,
  `West` (colloquial, not URA: Katong is East). Read from the headline, else a short or unit-numbered
  excerpt; a post that says "all outlets", "islandwide" or "except …" gets none. A missing `places`
  means NOT STATED, never "islandwide".
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

## `attrs` (every deal) and `full`

```json
"attrs": {"cost": "free", "price": null, "needs": ["member", "min-spend"], "min_spend": 30,
          "checked": true, "ease": 76},
"full": true
```

Structured attributes read from the post's own words by `lobang/attrs.py` (deterministic, no LLM):
- `cost`: what the deal gives: `free` (headline says free), `1-for-1`, `pct-off`, `cheap`, or `null`.
- `price`: the lowest `$` price in the headline, or `null`.
- `needs`: what the reader must do or be, in this order, from this vocabulary only: `contest` (lucky
  draw), `eligible` (students, seniors…), `card` (a specific bank card), `member`, `app`, `min-spend`,
  `purchase`, `group`, `booking`, `first-n` (explicit cap), `social`, `delivery`, `code`, `one-day`,
  `days`, `hours`. Unknown values must be ignored by the page.
- `checked`: the post had enough text to look. `needs: []` with `checked: false` means UNKNOWN,
  never "no catch"; the page shows nothing for it.
- `ease`: 100 minus the cost of `needs`. Promos move in Hot by it (`attrs.ease_points`); the page's
  Easy to claim filter keeps promos with `checked`, `ease >= 80` and no `contest`.
- The loose `member` / `app-only` / `card` tags are kept only when `needs` agrees.
- `full: true`: `details.json` holds more of the post than `summary`. Absent otherwise.

## `public/details.json` and `public/vectors.json`

Written by the same collect as `deals.json`, fetched by the page only when needed (first card
expanded, first search typed). Either may be missing or older than `deals.json`: the page then
falls back to the summary and to word search, never to an error.

```json
{"schema": 1, "generated_at": "...", "details": [{"id": "d_3f9a1c2b7e", "body": "Para one.\nPara two.\n…"}]}
{"schema": 1, "generated_at": "...", "model": "potion-retrieval-32M/pca256/int8", "dim": 256,
 "vectors": [{"id": "d_3f9a1c2b7e", "v": "<base64 of 256 signed bytes: the unit vector x127>"}]}
```

- `body`: the post's full text, one paragraph per line, at most 5,000 chars; a final line `…` means
  the collector clipped it. Display only: the classifier never reads it.
- `v`: the deal's embedding (`lobang.embed.deal_text`). The page embeds the query with the same
  model (`public/embed.js` + `public/embed/`) and ranks by cosine. Changing the model means
  rebuilding `public/embed/` (`tools/build_embed_model.py`) and bumping `sw.js` CACHE.

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
