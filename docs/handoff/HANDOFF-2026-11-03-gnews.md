# Handoff: fleet-watchdog "sources answering" alert (lobang-leh)

Cloud session, 2026-11-03 to 04. Both changes are merged to `main`. There's no open work, only follow-ups.

## The problem
fleet-watchdog reported `DOWN lobang-leh sources answering 22 of 32 answering (min 75%)`.

- **Cause:** in the 2026-11-03 00:01Z collect, all 10 `gnews_*` sources got **HTTP 503** from Google News in the same run. Nothing retried them. The other 22 sources were fine.
- **Not actually recurring:** every `data/state.json` commit since 2026-10-22 had at least 30/32 answering. The watchdog kept reporting the same bad run because `state.json` doesn't change until the next collect.
- **Structural issue:** the gnews sources all hit one host, so they fail together. 10 of 32 meant that one Google outage on its own put the fleet below 75%.

## What changed (both merged to `main`)

### PR #1: retries and a Google News lane (merge `0570b2a`)
https://github.com/searchinginthedark/lobang-leh/pull/1
- `lobang/net.py`: `get()` retries HTTP 429/500/502/503/504 and network errors twice (after 3s, then 10s). It follows `Retry-After`, capped at 30s. Other HTTP errors (403, 404, ...) fail immediately. `FetchError` gained `transient` and `wait`.
- `lobang/sources.py`: gnews requests run one at a time behind `GNEWS_LOCK`, 1.5s apart (`GNEWS_GAP`). A breaker: once one query has used up its retries, the rest of that run get a single 10s attempt (`GNEWS_TRIPPED_TIMEOUT`). Without it, a hanging Google could push the job past `collect.yml`'s 10-minute timeout. `gnews_reset()` clears that state at the start of each run.
- `lobang/fetch.py`: `run()` sends gnews sources to their own 1-worker pool and everything else to the 8-worker pool. Results go back in config order.
- `tests/test_sources.py`: new `NetRetry` and `GnewsLane` classes cover retries, `Retry-After`, giving up, no retry on 404, the gnews requests never overlapping, the breaker, and result order.

### PR #3: Google News cut from 10 queries to 5 (merge `41cf398`)
https://github.com/searchinginthedark/lobang-leh/pull/3
- Only `config/sources.yml` (and the CHANGELOG) changed. There are now 27 active sources, 5 of them gnews, so a full Google outage leaves 22/27 = 81%.
- **Kept:** `gnews_new_opening`, `gnews_promo_fnb`, `gnews_1for1`, `gnews_chain_promo`. These are the four with the most deals no other source found (18/17/5/3 out of 611 deals).
- **Merged:** `gnews_first_outlet` now uses `'"first outlet in Singapore" OR "first Singapore outlet" OR "first store in Singapore"'`, which absorbs `gnews_flagship`.
- **Disabled** (`disabled: true`, with the reason in each entry): `gnews_flagship`, `gnews_buy1get1`, `gnews_free_food`, `gnews_bubbletea`, `gnews_overseas_brand`. Together they were the only source for about 6 deals.
- I deliberately didn't OR-merge the keyword queries. Google binds OR tighter than the implicit AND (`a b OR c d` = `a (b OR c) d`), so a merged keyword query searches for something else. Only exact phrases were merged.

## Verified after merge
- The 2026-11-04 00:01Z collect, the first run with both changes, succeeded. **27/27 answering.** The full unit suite passed in CI; it runs before the collect step and uses the real `feedparser`, which I couldn't install in the cloud session.
- That run's gnews counts (items / F&B): promo_fnb 27/9, 1for1 29/12, chain_promo 32/11, **first_outlet 5/5**, new_opening 33/14. The merged query returned only F&B items in its first run.

## Follow-ups for you
1. **Around 2026-11-10:** run `python tools/source_yield.py`. Check that `gnews_first_outlet` isn't mostly non-food noise; the merged query no longer requires `food`. If it is, revert that entry.
2. **Don't add gnews queries back casually.** With 22 other sources, the floor survives a full Google outage only while gnews is at most 7 sources.
3. **Optional, in the fleet-watchdog repo** (not reachable from the cloud session): alert only after **2 bad runs in a row** instead of 1. That ignores one-off blips like this one and still catches real outages. I advised against counting upstream hosts instead of sources: a Google outage would then read as 1 host out of about 20 and never alert. I haven't checked whether the watchdog already debounces.

## Still not covered
- If Google blocks GitHub runner IPs for hours, retries don't help. That case is now just 5 sources failing, though, not an alert.
- `docs/sources-probe.md` still lists the disabled queries as KEPT. It's a dated snapshot from 2026-10-03, and earlier disables didn't update it either.

## Branch state
`claude/keen-gauss-c0gx7i` is identical to `main` and has nothing left to merge. Pull `main` locally:
```bash
git checkout main && git pull origin main
```
