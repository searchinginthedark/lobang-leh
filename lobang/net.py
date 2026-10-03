"""One HTTP helper for every source.

Which User-Agent a source accepts is a measured fact per source (config/sources.yml
`ua:`), not a style choice: some food blogs sit behind Cloudflare and refuse a
library UA, while Google News answers either.
"""

from __future__ import annotations

import gzip
import urllib.error
import urllib.request

LIBRARY_UA = "lobangleh/1.0 (+https://github.com/Zhiyang123/lobang-leh; personal deal feed)"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/148.0 Safari/537.36")


class FetchError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def get(url, ua="browser", timeout=25):
    """Body bytes. Raises FetchError on any non-2xx or network failure."""
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
        raise FetchError("HTTP {0}".format(exc.code), status=exc.code)
    except (urllib.error.URLError, OSError, EOFError) as exc:
        raise FetchError("unreachable: {0}".format(exc))
