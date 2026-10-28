# Restyle plan: Sticker Scrapbook + Juicy accents

Chosen by the user on 2026-10-13 from the mockups at https://claude.ai/artifact/MHW4T6yijHX17C1HD9EUZ9
(private to the user). Preference, most liked first: **Concept 4 (Sticker Scrapbook), Concept 2 (Juicy),
Concept 1 (Voucher)**. Build a mix of 4 and 2, with 4 as the base. Take nothing from Concept 1.

This file is the handover for a NEW session. Read it whole before the first edit.

## How to start the new session

1. Open the session in `lobang-leh/` (so the brief and `.claude/launch.json` load).
2. Set the model to **Opus 5.5** and effort to **high** in the session controls.
3. First message (paste as is):

   > Read docs/restyle-plan.md and run it step by step. Plan first, show me the plan, then build.
   > Avoid: cream or off-white backgrounds, pill-shaped controls, italic accent words, numbered
   > 01/02/03 labels, monospace labels.

## What the look is

**From Concept 4 (the base):**
- Background: sage paper with a faint dot grid (mockup: `#e4efe9`, dots `#b9cfc2`, 18 px spacing).
  This replaces the cream `--bg: #faf6ee`, which is on the fleet's avoid list.
- **Bagel Fat One** (OFL) for the brand, view tabs and the small kind label only. Never for headlines
  or body: it is unreadable in long runs. Body stays **Plus Jakarta Sans** (already self-hosted).
- White cards; alternate cards tilt by about ±0.6deg. Headlines stay level enough to read.
- A food **sticker** on each card, top right, white outline, rotated 10deg. Real build uses
  **Microsoft Fluent Emoji 3D** PNGs (MIT), never system emoji.
- Save gives a small sparkle burst.
- At most one piece of tape, on the top Hot card only. More than one turns into clutter.

**From Concept 2 (accents only):**
- **Kaya toast mascot** (inline SVG, 3 colours, 5 shapes; spec in the mockup's `.v2 .mascot`). Appears
  in the header, empty states, the Birthday view and the tour. Never on cards.
- **Pressable 3D controls**: thick bottom edge (`border-bottom: 4px`) that flattens on `:active`.
  Applies to the Save button, tabs, filter button and area chips. Cards stay flat.
- Mascot speech bubble at the top: "N new lobang since you last looked", from the existing
  `lobang:seen` key. Hide it when N is 0.
- Do NOT add Nunito. One new font (Bagel Fat One) is the budget.

**Must not change:**
- **Red = promo, blue = opening** on every card (chosen for colour-blind users).
- Radii stay `--r-ctl` 10px / `--r-tag` 6px. No pills.
- Birthday perks keep their "Birthday" label.

## Sticker map

Map on the deal's `category` (12 live values on 2026-10-13; re-check with
`python -c "import json,collections;print(collections.Counter(x.get('category') for x in json.load(open('public/deals.json',encoding='utf-8'))['deals']))"`):

| category | sticker idea |
|---|---|
| restaurant | 🍜 steaming bowl |
| bakery-dessert | 🍰 shortcake |
| buffet, hawker, fast-food, delivery | 🍛 🍢 🍔 🛵 |
| coffee, cafe, bubble-tea, bar-drinks | ☕ 🥐 🧋 🍹 |
| grocery, other | 🛒 🍽️ |

Plus `opening` → 🎉 overlay or a separate sticker, `birthday` → 🎂. About 16 PNGs at 96 px, target
under 150 KB total. Unknown category falls back to 🍽️; a missing file must not break the card.

## Steps, model and effort

| # | Step | Model · effort | Why this level |
|---|---|---|---|
| 1 | Plan: tokens (light AND dark palette, the mockup has light only), component list, sticker map, mascot spec, tour changes | **Opus 5.5 · high** | Taste and judgement calls. Medium tends to fall back to stock styles. |
| 2 | Fetch assets: Bagel Fat One latin woff2, Fluent Emoji 3D PNGs + its LICENSE | **Sonnet 5.5 · low** | Mechanical. The user must approve each download. |
| 3 | Build CSS + markup against the step-1 contract | **Sonnet 5.5 · medium** (one subagent) | Fixed contract, small files (`app.css` 15 KB, `index.html` 8 KB). |
| 4 | Build JS: sticker picker, mascot bubble count, save burst, tour step text | **Sonnet 5.5 · medium** | Same contract. Tour edits are reviewed in step 5. |
| 5 | Verify (see checklist) | **Opus 5.5 · high** | Catches specificity, contrast and tour regressions. |
| 6 | Ship: commit, `git pull --rebase`, push, `/release` | **Opus 5.5 · medium** | Routine, but CI commits to `main`, so watch the rebase. |

Do not use xhigh or max: the app is small and no step runs long enough to pay for it.

## Gotchas this app already learned

- **CSP** (`vercel.json`): `img-src 'self' data:` already allows self-hosted PNGs. Fonts need
  `font-src 'self'`, which is set. Nothing else needs a new directive. Load nothing from a CDN.
- **Service worker**: bump `CACHE` in `public/sw.js` (currently `lobang-v9`; re-read it). Add the new
  font and stickers to the precache one at a time (`c.add(a).catch(()=>{})`), never `addAll`.
- **Tour**: update `#tour-steps` in `index.html` FIRST, then `FLOW` in `tests/test_tour.py`. Tour is at
  its 8-step cap: merge, do not add.
- **Motion**: the `prefers-reduced-motion` block goes AFTER the rules it overrides and names every
  mover (mascot bob, button press, save burst). Tilt is not motion and can stay.
- **Fonts**: add Bagel Fat One's licence beside `fonts/OFL.txt`.
- **Pane checks**: unregister the service worker and delete caches before trusting any check, stub
  `alert`/`confirm`/`prompt`, resize to 375x600 before overflow checks.
- `.list` keeps `grid-template-columns: minmax(0, 1fr)`. Tilted cards must not cause sideways scroll.
- Optional: the mascot as the home-screen icon. iOS only picks up a new icon on remove + re-add, and
  removing the app DELETES saved deals and settings. Export first, or add the new copy before removing
  the old one. Ask the user before doing this.

## Verify checklist (step 5)

- `python -m unittest discover -s tests` passes (137 on 2026-10-11; read the count it prints).
- `/ui-check` on `public/` shows no new violations.
- At 375 px wide, light AND dark: no sideways scroll, stickers do not cover headlines, tabs fit.
- Red/blue kind colours pass contrast on the new background in both themes.
- Reduced motion on: no bob, no burst.
- The service worker shim test still serves `./` network-first.
- After deploy: on the phone, fully close and reopen the app twice, then check one card of each kind.
