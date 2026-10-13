# Restyle contract (step 1 of docs/restyle-plan.md)

Written 2026-10-13. The fixed contract steps 3 and 4 build against. Base = Concept 4 (Sticker
Scrapbook), accents from Concept 2 (Juicy). Never use: cream/off-white backgrounds, pill shapes
(no radius above 10px on a control, never 999px), italic accent words, 01/02/03 labels, monospace.

## 1. Tokens (`public/app.css` `:root`)

| token | light | dark | note |
|---|---|---|---|
| `--bg` | `#e4efe9` sage | `#111915` | replaces cream `#faf6ee` |
| `--dot` | `#b9cfc2` | `#1f2c25` | dot grid, 18px spacing |
| `--surface` | `#ffffff` | `#1b2520` | cards, inputs |
| `--text` / `--ink` | `#1f2a24` | `#e8f0eb` | `--ink` = selected tab bg, Save-on bg |
| `--on-ink` | `#ffffff` | `#111915` | text on `--ink` |
| `--muted` | `#4b5a51` | `#a3b5aa` | 6.2:1 / 8.3:1 on bg |
| `--line` | `#cddcd3` | `#2c3a33` | borders |
| `--edge` | `#b3c6bb` | `#0a0f0c` | the pressable bottom edge |
| `--red` | `#c82626` | `#d63333` | promo; dark nudged so the tag clears 3:1 on the card |
| `--blue` | `#1f5fbf` | `#3070d6` | opening; same reason |
| `--brand` | `#c82626` | `#ff7468` | wordmark |
| `--tape` | `rgba(255,214,92,.75)` | `rgba(255,214,92,.45)` | |
| `--shadow` | `0 2px 0 rgba(31,42,36,.08)` | `none` | cards |

Keep every other existing token (`--green-*`, `--yellow-*`, `--red-bg/fg`, `--neutral-*`, `--link`,
`--focus`, `--on-red`) with its current values, except `--neutral-bg` light `#edf3ef` / dark `#26332c`
and `--neutral-fg` light `#33433a` / dark `#d6e2db` (the old ones were beige). White text on the dark
`--red`/`--blue` must stay >= 4.5:1; step 5 re-measures.

Radii unchanged: `--r-ctl` 10px, `--r-tag` 6px, `--radius` 16px (cards).

Dark mode stays `@media (prefers-color-scheme: dark) { :root {...} }` as today (the app has no theme
toggle).

Body: `background-color: var(--bg); background-image: radial-gradient(var(--dot) 1.2px, transparent 1.3px);
background-size: 18px 18px;`. The sticky `.tabs` bar keeps a SOLID `var(--bg)` (no dots).

## 2. Fonts

- `fonts/BagelFatOne-latin.woff2` (Fontsource latin 400), `@font-face` family `"Bagel Fat One"`,
  weight 400, `font-display: swap`. Preload it in `index.html` like Plus Jakarta Sans.
- `--display: "Bagel Fat One", var(--font);`
- Bagel is used ONLY on: `.brand`, `.tab`, `.kind`. Never headlines, body, buttons other than tabs.
- Licence: `fonts/OFL-BagelFatOne.txt`.

## 3. Components

**Header** (`.brand-row`): left group `.brand-lockup` = mascot (`.mascot.bob`, 40px) + `h1.brand`.
`.brand`: `font: 400 var(--t-brand)/1 var(--display); color: var(--brand); display: inline-block;
transform: rotate(-2deg); letter-spacing: 0`. Right group unchanged (`?`, Refresh).

**New-since bubble** `<p class="bubble" id="newsince" hidden>` directly under `.brand-row`, before
`.sub`. One line, `--t-label`, weight 700, white `--surface`, 1px `--line` border, radius 10px,
padding 6px 10px, `display: inline-block` width, a small CSS triangle tail on its top-left edge pointing
at the mascot (`::before`, border trick, same colours). Text, not a control. Flat (no 3D edge: that
look means "you can press this").

**Tabs** (`.tab`): Bagel, `--t-label` (13px), `font-weight: 400`, `line-height: 1.1`. Unselected:
`--surface` bg, `--text`, 1px `--line` border. Selected: `--ink` bg, `--on-ink` text, `--ink` border,
`transform: rotate(-1.5deg)`. Red is NOT used for the selected tab (red means promo). Labels stay
"Ending soon", "New openings" (the tour test pins them); they may wrap to 2 lines, never overflow.
>= 600px: `--t-body`.

**Pressable 3D** (Save `.act[data-act="save"]`, `.tab`, `.filter-btn`, `#areas .chip`): the thick
bottom edge is a hard shadow, not a border, so pressing never shifts layout:
`box-shadow: 0 4px 0 var(--edge); transition: transform .08s, box-shadow .08s;`
`:active { transform: translateY(4px); box-shadow: 0 0 0 var(--edge); }`
Selected tab: `:active` = `rotate(-1.5deg) translateY(4px)`. Nothing else gets the 3D edge; cards are
flat. Save needs a marker: JS sets `data-act="save"` on the Save button (Share has `data-act="share"`
and stays flat). Save on (`aria-pressed="true"`): `--ink` bg, `--on-ink` text, `--ink` border.
Area chip on keeps the green + tick. Keep the existing `.icon-btn:active { transform: scale(.97) }`
for the other icon buttons, but `.filter-btn:active` uses the 3D press instead.

**Cards** (`.card`): `position: relative; background: var(--surface); border: 1px solid var(--line);
border-radius: var(--radius); box-shadow: var(--shadow); padding: 16px 14px 14px;`
REMOVE the 6px left colour bar (`border-left`) and `.card.opening` border colour: the filled kind tag
carries red/blue + words. Tilt (articles only, so `.show-more` never counts):
`.card:nth-of-type(4n+2) { transform: rotate(.6deg) }`, `.card:nth-of-type(4n+4) { transform: rotate(-.6deg) }`,
others level. `.list` keeps `grid-template-columns: minmax(0, 1fr)`; gap becomes 20px and
`padding-top: 18px` so stickers poking above a card never touch the one above.

**Kind tag** (`.kind`): `font: 400 var(--t-label)/1.2 var(--display); padding: 3px 8px 2px;
border-radius: var(--r-tag); background: var(--red); color: #fff; letter-spacing: .01em;
text-transform: none; transform: rotate(-2deg); display: inline-block`. `.card.opening .kind` uses
`--blue`. Text stays "Promo" / "New opening" / "Birthday" (sentence case, no tracked caps).

**Eyebrow**: `padding-right: 56px` so the sticker never covers the merchant name. Headline unchanged
(Plus Jakarta 700, level).

**Sticker** `<img class="sticker" src="stickers/<file>.png" alt="" width="48" height="48"
loading="lazy" decoding="async">`, first child of `.card`:
`position: absolute; top: -18px; right: 10px; width: 48px; height: 48px; transform: rotate(10deg);
pointer-events: none;` white die-cut outline:
`filter: drop-shadow(2px 0 0 #fff) drop-shadow(-2px 0 0 #fff) drop-shadow(0 2px 0 #fff)
drop-shadow(0 -2px 0 #fff) drop-shadow(0 3px 3px rgba(0,0,0,.18));`
Dark: outline colour `#e8f0eb` (a sticker is still white-edged, just not glaring). Even tilted cards:
`.card:nth-of-type(even) .sticker { transform: rotate(-12deg) }`.

**Tape**: one piece, top Hot card only. JS adds class `taped` to card 0 when `state.view === 'hot'`.
`.card.taped::before { content: ""; position: absolute; top: -9px; left: 22px; width: 64px;
height: 18px; background: var(--tape); transform: rotate(-4deg); pointer-events: none; }`

**Save burst**: 6 `<span class="burst">` appended to the Save button (`position: relative;
overflow: visible` on `.act`). Each is an 8px CSS 4-point sparkle (`clip-path: polygon(50% 0, 61% 39%,
100% 50%, 61% 61%, 50% 100%, 39% 61%, 0 50%, 39% 39%)`), colours cycling `#ffc828`, `var(--red)`,
`var(--blue)`. Animation `burst .6s ease-out forwards` from centre to `--x/--y` (radius ~30px), fade
out. No emoji. JS removes spans after 700ms. Not created at all under reduced motion.

**Mascot** (kaya toast). One `<svg>` sprite at the top of `<body>`:
`<svg width="0" height="0" style="position:absolute" aria-hidden="true">` is NOT allowed (CSP
`style-src 'self'` blocks inline style attributes) -> use `class="sr"` on the sprite svg instead.
`<symbol id="kaya" viewBox="0 0 64 64">`: `rect x8 y14 w48 h42 rx14 #e9a54b` (crust), `rect x13 y19
w38 h32 rx10 #fbe3a6` (bread), `rect x13 y33 w38 h5 #7fb35b` (kaya), two `circle r3 #2b2f36` at
(25,27) (39,27), `path d="M27 43q5 4 10 0" stroke #2b2f36 stroke-width 3 fill none round cap`.
Fixed colours in both themes (it is an illustration). Uses: `<svg class="mascot" viewBox="0 0 64 64"
aria-hidden="true"><use href="#kaya"/></svg>`.
- Header: 40px, class `bob` (`animation: bob 2.4s ease-in-out infinite; transform-origin: 50% 90%`,
  keyframes rotate -4deg <-> 4deg + translateY(-2px)).
- Empty states (`showState('empty', ...)`): 64px, centred above the heading, static. Not on errors.
- Birthday box: 36px, left of "Your birthday" in `.bday-head` (flex row), static.
- Tour: 48px in `.tour-card` before `#tour-n`, class `tour-mascot`, shown only on centred steps
  (`.tour-card.mid .tour-mascot` visible, otherwise `display: none`), static.
- Never on cards.

**Untouched**: filters panel layout, search, category chips (flat), health list, toast, state box
(except the mascot), birthday picker selects.

**Manifest**: `background_color` `#fff8ec` (cream) -> `#e4efe9`. Icons unchanged (home-screen icon swap
is out of scope: iOS needs remove + re-add, which deletes saved deals).

## 4. Sticker map (JS `STICKER`, files in `public/stickers/`, 96x96 PNG)

| key | file | Fluent Emoji 3D |
|---|---|---|
| restaurant | `restaurant.png` | Steaming bowl |
| bakery-dessert | `bakery-dessert.png` | Shortcake |
| buffet | `buffet.png` | Curry rice |
| hawker | `hawker.png` | Oden |
| fast-food | `fast-food.png` | Hamburger |
| delivery | `delivery.png` | Motor scooter |
| coffee | `coffee.png` | Hot beverage |
| cafe | `cafe.png` | Croissant |
| bubble-tea | `bubble-tea.png` | Bubble tea |
| bar-drinks | `bar-drinks.png` | Tropical drink |
| grocery | `grocery.png` | Shopping cart |
| other (+ fallback) | `other.png` | Fork and knife with plate |
| birthday | `birthday.png` | Birthday cake |

Pick: birthday perk (`bday` truthy in `card()`) -> `birthday`; else `STICKER[d.category]` if the key
exists; else `other`. Openings use their category sticker (the blue tag already says "new"); no
party-popper, one sticker per card. A load error removes the `<img>` (`addEventListener('error')`,
never an inline `onerror`: CSP). Licence: `stickers/LICENSE` (MIT, Microsoft).

## 5. JS changes (`public/app.js`)

1. **New-since count.** `tourInit` already reads then overwrites `lobang:seen`. Capture the value it
   READ into a module var `lastSeen` before the write. After each successful `load()`, set
   `#newsince`: N = deals with `ts(d.first_seen) > lastSeen`. Hidden when `lastSeen` is 0 (first visit,
   or storage blocked) or N is 0. Text: `N new lobang since you last looked` (no plural change;
   "lobang" is invariant). Counts all deals, every view.
2. **Sticker** per section 4, prepended in `card()`.
3. **Tape**: `render()` adds `taped` to card 0 when `state.view === 'hot'`.
4. **Save in place.** The Save handler must not rebuild the list in non-Saved views (the burst would
   be destroyed with the button): toggle `saved`, `saveSaved()`, then set the button's text +
   `aria-pressed`, then burst if now saved and motion allowed; call `render()` only when
   `state.view === 'saved'`. Reduced motion = `window.matchMedia &&
   matchMedia('(prefers-reduced-motion: reduce)').matches`, checked at click time.
   Set `data-act="save"` / `data-act="share"` on the two `.act` buttons.
5. **Mascot in empty states**: `showState` prepends the mascot svg (built with `createElementNS`,
   `use` with `href="#kaya"`) when `kind === 'empty'`.
6. No new buttons and no new `el('button', ...)` classes: the tour test pins them.

## 6. Tour (`index.html #tour-steps`, still 8 steps; then `tests/test_tour.py`)

- Step "Is this up to date?": add one sentence: "When deals arrived since your last visit, the
  speech bubble under the name says how many."
- Step "Reading a card": "red PROMO or blue NEW OPENING" -> "a red Promo or blue New opening label";
  add "The sticker shows the kind of food." Keep everything else, incl. "area"/"MRT" words.
- Then, in `test_tour.py`, `MUST_MENTION`: "PROMO" -> "Promo", "NEW OPENING" -> "New opening".
  FLOW unchanged (no new controls).

## 7. Service worker, motion

- `public/sw.js` CACHE `lobang-v9` -> `lobang-v10`; ASSETS add `./fonts/BagelFatOne-latin.woff2` and
  the 13 `./stickers/*.png`, still added one at a time.
- The `prefers-reduced-motion` block stays LAST in `app.css` and names every mover:
  `.bob, .burst, .tab, .act, .filter-btn, .chip { animation: none !important; transition: none !important; }`
  plus the existing universal rule. Tilt and rotations are static and stay.
