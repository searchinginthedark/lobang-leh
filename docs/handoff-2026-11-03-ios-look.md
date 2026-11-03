# Handoff: iOS look, SwiftUI-style motion, filter sheet (2026-11-03)

Written for a local Claude Code session picking up this work. Everything below is **merged to
`main` and live in production**:
[searchinginthedark/lobang-leh#2](https://github.com/searchinginthedark/lobang-leh/pull/2), merge
commit `a1102a7`, and the Vercel production deploy succeeded. Run `git pull` on `main` before you
start. The feature branch `claude/affectionate-albattani-8jcn9s` is finished; do not reuse it.

## 1. What changed, in one paragraph

The PWA (`public/`) now has **two looks**: **iOS** (new, the default), modelled on the App
Store's Today tab, and **Sticker** (the existing Sticker Scrapbook look, unchanged). A
half-circle button in the header (`#skin-btn`) switches between them, and the choice is saved
in `localStorage` key `lobang:skin`. On top of the iOS look sit six SwiftUI-style animations
plus the Filters panel as a bottom sheet. Everything iOS-specific is scoped under `html.ios`, so
the Sticker look renders exactly as before.

## 2. The user's decisions (do not reopen these without asking)

| Question | Choice |
|---|---|
| Which reference app for the iOS look? (offered: App Store Today, Apple News, Things 3, Flighty) | **App Store Today** |
| What are the "2 modes"? (offered: light/dark, or iOS/current) | **iOS look and the current Sticker look**, user-toggleable. Light/dark still just follows the phone. |
| Which SwiftUI effects? | Claude picked; the user approved and asked for the filter sheet next. |
| Default look | iOS. Claude chose this; the user merged with it. Flip it in `public/skin.js` if asked. |

Effects deliberately **not** built, with the reason given to the user:
- **Animated gradient backgrounds:** decorative, cost battery, clash with the plain grouped look.
- **Haptics:** iPhone web apps can't trigger vibration.
- **Number-change animations:** too little visible gain.

**How the user wants answers:** direct and concise, the most useful thing first, no filler or
praise. Push back on weak ideas; don't agree by default. They like being given a short list of
options to pick from for design choices.

## 3. Where things live

| File | What's there |
|---|---|
| `public/skin.js` (new) | Runs in `<head>` before first paint: puts `.ios` on `<html>` unless `lobang:skin === 'sticker'`, and sets `meta[name=theme-color]`. Exposes `window.LobangSkin.get()/set()`. It's an external file because the CSP is `script-src 'self'`, which blocks inline scripts. |
| `public/index.html` | SVG sprite gains line icons `#i-hot #i-ending #i-new #i-birthday #i-saved #i-refresh #i-bell #i-skin #i-close`. Adds `#skin-btn`, `#ios-date`, `#view-title`, `#nav-inline`, `#sheet-dim`, and `.sheet-head` with `#filters-done`. Each tab is now `<svg class="ico ios-only">` + `<span class="tab-lbl">Label</span>`. Bell and Refresh carry an iOS icon plus a `.sticker-only` span. |
| `public/app.css` | The Sticker CSS is untouched above line ~460. Then: the **iOS look** block (~463: tokens, nav bar, cards, tab bar, filters, toast, tour), the **iOS motion** block (~745: effects 1-6), and the **filter sheet** block (~835). The reduced-motion block stays last on purpose. |
| `public/app.js` | `expand()` inside `card()` (~657) is the old summary toggle, refactored. The iOS helpers around ~833-990: `isIOSLook`, `icon`, `bounce`, `zoomCard`, `zoomSwipeInit`, `filtersOpen`, `sheetDragInit`, `navCollapseInit`, `skeleton`. `paintSkin`/`toggleSkin`/`paintDate` sit around ~1177. `renderControls()` sets `#view-title`, `#nav-inline-title` and `--i` on `#tabs` (the tab-lens position). |
| `public/sw.js` | `CACHE = 'lobang-v19'`; `skin.js` is precached. |
| `tests/test_tour.py` | FLOW `page` gains `skin-btn` and `filters-done`; `js_buttons` gains `zoom-close`; MUST_MENTION gains `iOS look`, `Sticker look`, `full screen`, `swipe down`, `Done`, `sheet`. |
| `features.json` | New features `skin`, `zoom` and `filter-sheet`. `views` reach text updated. `clear` gains a `#filters-done` step, because the sheet covers Clear filters. |
| `CHANGELOG.md` | Entries v2026.11.03, .2 and .3. |

## 4. How each piece works

**The two looks.** iOS styles are `.ios <selector>`, placed after the Sticker rules they
override. Watch out for the Sticker rules that use IDs (`#areas .chip`, `#digest-btn[...]`,
`#tour-skip`): `.ios .x` loses to them, so the iOS overrides repeat the ID. `.ios-only` is
`display:none` unless in the iOS look; `.sticker-only` is hidden in the iOS look. iOS colours are
Apple system colours, but where the stock value fails WCAG AA for small text the Increased
Contrast variant is used: `--muted #6c6c70` and `--link #0066cc` in light, `#98989f` and
`#409cff` in dark. Text uses `font: -apple-system-body`, so it follows Dynamic Type on Apple
devices and is 17px elsewhere.

**Motion** (iOS look only; all of it is off under `prefers-reduced-motion` through the existing
final block):
1. **Zoom:** `zoomCard()` toggles `.zoomed` (the card goes `position:fixed` and fills the
   screen) inside `document.startViewTransition`, with `view-transition-name: zoom-card` set only
   while it runs. Opening calls `expand(true)` so the full post loads. Close button
   (`.zoom-close`, built in JS), Escape, or a swipe down of more than 110px. A `render()` while a
   card is open releases `zoom-lock`. Without View Transitions it swaps instantly.
2. **Tab lens:** `.tabs::before`, positioned by `--i` with `--spring`, a CSS `linear()` spring
   curve.
3. **Collapsing title:** an IntersectionObserver on `#view-title` toggles `#nav-inline.show`.
4. **Scroll-in cards:** `animation-timeline: view()` inside `@supports`.
5. **Icon animations:** `bounce(node, 'bounce'|'wiggle')` on tab icons, Save and the bell;
   Refresh spins while `:disabled`.
6. **Loading shimmer:** `skeleton()` adds `.card.skeleton` placeholders from `load()` when there
   is no data yet; `render()` clears them.

**Filter sheet:** `filtersOpen(open)` replaces the old inline toggle. In the iOS look it adds
`role=dialog` and `aria-modal`, unhides `#sheet-dim`, puts `sheet-lock` on `<html>` and focuses
Done. Closing adds `.closing`, waits 300ms, then hides; a re-tap mid-close reopens. Two heights:
the default (~360px) and `.detent-large`, set by dragging the header up by 50px or more, or by
focusing `#q`. Dragging down by more than 90px drops to the default height, or closes from it.
`toggleSkin()` closes the panel first. In the Sticker look the panel stays inline and Done sits
at its foot (`order: 9`).

## 5. Rules this repo enforces (any UI change must follow them)

- **New control → update three places in the same commit:** the tour steps in `index.html`
  `#tour-steps`, then FLOW / MUST_MENTION in `tests/test_tour.py`, and a feature in
  `features.json` (`test_features.py` fails on unmapped control ids). Never update FLOW alone.
- **CSP:** `default-src 'none'`, `script-src 'self'`, `style-src 'self'`. No inline
  `<script>`, no `style=""` attributes and no `setAttribute('style')`. Setting styles from JS via
  `el.style.setProperty(...)` (the CSSOM) is fine.
- **Changed a cached asset → bump `CACHE` in `public/sw.js`.**
- **Style both looks**, and check reduced motion.
- **Tap targets stay at least 44px.** iOS capsules get a 44px box with a smaller visible pill:
  `border: 5px solid transparent; background-clip: padding-box`.
- **`docs/restyle-contract.md` covers only the Sticker look.** Its no-pills rule and "the app has
  no theme toggle" line don't apply to the iOS look. The contract was not updated; consider
  adding a note there.

## 6. How to verify

```bash
python -m unittest tests.test_tour tests.test_features
```

```bash
python -m unittest discover -s tests
```

In the cloud container, `feedparser` would not install (`sgmllib3k` failed to build), so the
`test_core`, `test_sources`, `test_birthday` and two `test_attrs` tests errored at import. Locally
`pip install -r requirements.txt` should fix that; that failure has nothing to do with this work.

Visual check: `cd public && python3 -m http.server 8765`, then open at 390x844 in both looks.
To pick a look, run `localStorage.setItem('lobang:skin','sticker')` or `'ios'` and reload. Add
`localStorage.setItem('lobang:tour','off')` to skip the tour.

`features.json` was driven through Playwright in both looks with reduced motion on and off,
minus `digest`, `share` and `report-copy` (they need push/clipboard stubs). All passed. The repo's
own runner, `python ../memory/tools/verify/verify.py .`, wasn't available in the cloud, so
running it locally would be a useful extra check.

## 7. Open items, in priority order

1. **Test on a real iPhone; nothing has been tried on one yet.**
   - Sheet drag distances (50px up / 90px down) and swipe-to-close (110px) were tuned with
     simulated touches in Chrome.
   - Whether the keyboard covers the bottom of the sheet when searching. If it does, resize the
     sheet from `visualViewport` resize events.
   - The glass blur strength (Chrome draws it weaker than Safari).
   - After deploy, a Home Screen install picks up `lobang-v19` on the next open; a full close and
     reopen may be needed.
2. **An open card isn't fully modal:** Tab can still reach controls behind a zoomed card or the
   sheet. Fix by setting `inert` on `.top`, `#tabs`, `#list` siblings and the like while one is
   open.
3. **At 320px**, "New openings" cuts off with an ellipsis in the tab bar. That's acceptable and
   how iOS itself behaves.
4. **The Sticker look's header buttons wrap onto a second row** at 375-390px. This predates the
   work; the 4th button didn't cause it.
5. **The preloaded Bagel/Jakarta fonts download in the iOS look too,** where they're unused.
   Harmless, and the service worker caches them.
6. **Possible next effects, if the user wants more:** number-change animations on counts, a
   matched-geometry animation for the "N new" banner, and pull-to-refresh styling.
