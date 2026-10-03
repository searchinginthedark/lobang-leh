"""Probe every source in config/sources.yml and print one line per source.

stdlib + feedparser only (no PyYAML: sources.yml uses a tiny flat subset parsed below).
Usage: python tools/probe_sources.py [--ua browser|library|auto] [--strict]
  auto (default): use each source's recorded `ua`; --strict exits 1 if any source returns 0 items.
Line format: name | type | status | items | newest | ua | ms
"""
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import feedparser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UAS = {
    "browser": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "library": "Python-urllib/3.9",
}


def load_sources(path=None):
    path = path or os.path.join(ROOT, "config", "sources.yml")
    out, cur = [], None
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#") or line.strip() == "sources:":
                continue
            m = re.match(r"^\s*-\s+(\w+):\s*(.*)$", line)
            if m:
                cur = {}
                out.append(cur)
            else:
                m = re.match(r"^\s+(\w+):\s*(.*)$", line)
            if not m or cur is None:
                continue
            k, v = m.group(1), m.group(2).strip()
            if v[:1] == '"' and v[-1:] == '"':
                v = v[1:-1]
            elif v[:1] == "'" and v[-1:] == "'":
                v = v[1:-1].replace("''", "'")
            else:
                v = re.sub(r"\s+#.*$", "", v)
            cur[k] = v
    return out


def source_url(s):
    if s["type"] == "rss":
        return s["url"]
    if s["type"] == "telegram":
        return "https://t.me/s/" + s["channel"]
    q = urllib.parse.quote(s["query"] + " when:7d")
    return "https://news.google.com/rss/search?q=%s&hl=en-SG&gl=SG&ceid=SG:en" % q


def fetch(url, ua):
    req = urllib.request.Request(url, headers={"User-Agent": UAS[ua], "Accept": "*/*",
                                               "Accept-Language": "en-SG,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:
        return 0, b""


def probe(s, force_ua="auto"):
    ua = s.get("ua", "browser") if force_ua == "auto" else force_ua
    if ua not in UAS:
        ua = "browser"
    t0 = time.time()
    status, body = fetch(source_url(s), ua)
    items, newest = 0, ""
    if status == 200:
        if s["type"] == "telegram":
            txt = body.decode("utf-8", "replace")
            items = len(re.findall(r'class="tgme_widget_message_text', txt))
            times = re.findall(r'<time[^>]*datetime="([^"]+)"', txt)
            newest = max(times)[:10] if times else ""
        else:
            ents = feedparser.parse(body).entries
            items = len(ents)
            ts = [e.get("published_parsed") or e.get("updated_parsed") for e in ents]
            ts = [x for x in ts if x]
            newest = time.strftime("%Y-%m-%d", max(ts)) if ts else ""
    return s["name"], s["type"], status, items, newest, ua, int((time.time() - t0) * 1000)


def main(argv):
    force = "auto"
    if "--ua" in argv:
        force = argv[argv.index("--ua") + 1]
    srcs = load_sources()
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda s: probe(s, force), srcs))
    bad = 0
    for n, t, st, it, nw, ua, ms in res:
        flag = "" if (st == 200 and it > 0) else "  <-- FAIL"
        bad += bool(flag)
        print("%-22s | %-8s | %3s | %3d items | newest %-10s | ua %-7s | %dms%s" % (n, t, st, it, nw or "-", ua, ms, flag))
    print("%d sources, %d failing" % (len(res), bad))
    return 1 if (bad and "--strict" in argv) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
