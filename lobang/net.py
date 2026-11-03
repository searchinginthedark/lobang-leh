"""One HTTP helper for every source.

Which User-Agent a source accepts is a measured fact per source (config/sources.yml
`ua:`), not a style choice: some food blogs sit behind Cloudflare and refuse a
library UA, while Google News answers either.
"""

from __future__ import annotations

import gzip
import time
import urllib.error
import urllib.request

LIBRARY_UA = "lobangleh/1.0 (+https://github.com/Zhiyang123/lobang-leh; personal deal feed)"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/148.0 Safari/537.36")


class FetchError(Exception):
    def __init__(self, message, status=None, transient=False, wait=None):
        super().__init__(message)
        self.status = status
        self.transient = transient
        self.wait = wait


# Statuses that mean "try again shortly", not "this source is broken". 2026-11-03 00:01Z:
# all 10 gnews sources returned HTTP 503 in one run (22/32 answering, under the
# fleet-watchdog's 75%) after answering normally 11 h earlier: a transient
# upstream blip, recorded as 10 dead sources because nothing retried.
RETRY_STATUS = {429, 500, 502, 503, 504}
RETRY_DELAYS = (3, 10)      # seconds before attempt 2 and 3
RETRY_AFTER_CAP = 30        # never honour a Retry-After longer than this


def _retry_after(exc):
    try:
        return min(float(exc.headers.get("Retry-After")), RETRY_AFTER_CAP)
    except (TypeError, ValueError, AttributeError):
        return None


def get(url, ua="browser", timeout=25, delays=RETRY_DELAYS, sleep=time.sleep):
    """Body bytes. Raises FetchError on any non-2xx or network failure.

    A transient failure (RETRY_STATUS, timeout, connection reset) is retried after each of
    `delays`; any other HTTP error (403, 404...) fails at once, since retrying cannot help."""
    for attempt in range(len(delays) + 1):
        try:
            return _get_once(url, ua, timeout)
        except FetchError as exc:
            if attempt == len(delays) or not exc.transient:
                raise
            sleep(exc.wait if exc.wait is not None else delays[attempt])


def _get_once(url, ua, timeout):
    hdrs = {
        "User-Agent": BROWSER_UA if ua == "browser" else LIBRARY_UA,
        "Accept": "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-SG,en;q=0.9",
        "Accept-Encoding": "gzip",
    }
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            if resp.headers.get("Content-Encoding", "").lower() == "gzip":
                body = gzip.decompress(body)
            return body
    except urllib.error.HTTPError as exc:
        raise FetchError("HTTP {0}".format(exc.code), status=exc.code,
                         transient=exc.code in RETRY_STATUS,
                         wait=_retry_after(exc) if exc.code in RETRY_STATUS else None)
    except (urllib.error.URLError, OSError, EOFError) as exc:
        # DNS failure, refused, reset, timed out: all worth one more try.
        raise FetchError("unreachable: {0}".format(exc), transient=True)
