# Scraper / API source contract

For sources with no RSS: a deal page to scrape, a site's internal JSON endpoint, or a
free-key API. One module per source in `lobang/scrapers/<parser>.py`.

## Registry entry (`config/sources.yml`)

```yaml
  - name: misslobang
    type: scrape            # scrape (HTML or a site's own JSON) | api (needs a free key)
    parser: misslobang      # module name in lobang/scrapers/
    url: https://...        # optional, the module may use it
    env: SOMEAPI_KEY        # api only: env var holding the key. Unset = source skipped, not failed
    publisher: Miss Lobang
    tier: deals             # deals | media | news | social
    scope: promo            # promo | opening | mixed
    fnb_only: true          # only if EVERY item is food & beverage
    ua: browser
    note: "measured <date>: N items, newest <date>"
```

## Module

```python
from lobang.net import FetchError

def fetch(src, get, key):
    """src: the registry dict. get(url, ua=..., timeout=...) -> bytes (raises FetchError).
    key: the API key string or None. Return a list of dicts:
      {"title": str, "url": str, "summary": str, "published": datetime | None,
       "publisher": str (optional, defaults to src["publisher"])}
    """
```

Rules (these protect the "a failure is never empty" invariant):
- **Raise `FetchError` when the expected structure is missing** (selector/JSON key not
  found, a challenge page, a login wall). Return `[]` only when the page is genuinely empty.
- Stdlib only (`re`, `json`, `html.parser`, `urllib.parse`) plus what is in
  `requirements.txt`. No headless browser, no new dependencies.
- At most 5 requests per run per source, 25 s timeout each (the default).
- `title` is the deal headline as the site shows it; never invent or summarise text.
- `url` must be the item's own page (absolute https), so it is a stable id.
- `published` is timezone-aware when the site gives a time; a naive datetime is taken as SGT.
- One offline test per module in `tests/test_scrapers.py` against a trimmed real fixture
  in `tests/fixtures/scrape_<name>.<html|json>` (< 40 KB), including one "markup changed"
  case that must raise.
