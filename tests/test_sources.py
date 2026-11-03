"""Parsers against real payloads captured 2026-10-03 (tests/fixtures, trimmed to ~5 items)."""

import io
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lobang import sources as S

FIX = os.path.join(ROOT, "tests", "fixtures")


def raw(name):
    with io.open(os.path.join(FIX, name), "rb") as fh:
        return fh.read()


class Rss(unittest.TestCase):
    def test_singpromos(self):
        items = S.parse_rss({"name": "singpromos", "publisher": "SingPromos", "type": "rss"}, raw("rss_singpromos.xml"))
        self.assertEqual(len(items), 5)
        for it in items:
            self.assertTrue(it["title"] and it["url"].startswith("http"))
            self.assertIsNotNone(it["published"])
            self.assertNotIn("appeared first on", it["summary"])
            self.assertNotIn("<", it["summary"])

    def test_ids_stable(self):
        a = S.parse_rss({"name": "x"}, raw("rss_eatbook.xml"))
        b = S.parse_rss({"name": "x"}, raw("rss_eatbook.xml"))
        self.assertEqual([i["id"] for i in a], [i["id"] for i in b])

    def test_garbage_is_an_error_not_empty(self):
        res_items = None
        with self.assertRaises(Exception):
            res_items = S.parse_rss({"name": "x"}, b"<html>Just a moment...</html>")
        self.assertIsNone(res_items)


class Gnews(unittest.TestCase):
    def test_publisher_suffix_stripped(self):
        items = S.parse_gnews({"name": "g", "type": "gnews"}, raw("gnews_sample.xml"))
        self.assertTrue(items)
        for it in items:
            self.assertNotEqual(it["publisher"], "Google News")
            self.assertFalse(it["title"].endswith(" - " + it["publisher"]), it["title"])


class Telegram(unittest.TestCase):
    def test_messages_parsed(self):
        for name in ("telegram_sgfooddeals.html", "telegram_kiasufoodies.html"):
            items = S.parse_telegram({"name": "tg", "type": "telegram"}, raw(name))
            self.assertGreaterEqual(len(items), 3, name)
            for it in items:
                self.assertTrue(it["url"].startswith("https://t.me/"))
                self.assertIsNotNone(it["published"])
                self.assertNotIn("&#036;", it["title"] + it["summary"])
                self.assertNotIn("&amp;", it["title"] + it["summary"])

    def test_brand_only_first_line_joined(self):
        page = (b'<div class="tgme_widget_message text_not_supported_wrap js-widget_message" data-post="ch/9">'
                b'<div class="tgme_widget_message_text js-message_text" dir="auto">\xf0\x9f\x8d\xa3 Sushiro \xf0\x9f\x8d\xa3<br/>'
                b'1-for-1 salmon sushi till 14 Oct<br/>T&amp;Cs apply</div>'
                b'<time datetime="2026-10-03T01:00:00+00:00" class="time">09:00</time></div>')
        it = S.parse_telegram({"name": "tg"}, page)[0]
        self.assertEqual(it["title"], "Sushiro: 1-for-1 salmon sushi till 14 Oct")
        self.assertEqual(it["summary"], "T&Cs apply")

    def test_price_kept_in_bare_line(self):
        self.assertEqual(S._bare("\U0001f37b \U0001f525 $9++ BAR BITES?! \U0001f440"), "$9++ BAR BITES?!")

    def test_nonexistent_channel_shell_is_an_error(self):
        with self.assertRaises(Exception):
            S.parse_telegram({"name": "tg"}, b"<html><body>Telegram</body></html>")


class ScraperPlumbing(unittest.TestCase):
    def test_module_rows_become_items_and_naive_time_is_sgt(self):
        import types
        from datetime import datetime
        fake = types.ModuleType("lobang.scrapers._fake")
        fake.fetch = lambda src, get, key: [
            {"title": "KFC 1-for-1", "url": "https://x/1", "summary": "<b>hi</b>", "published": datetime(2026, 10, 3, 9)},
            {"title": "", "url": "https://x/2"},   # no title: dropped
        ]
        sys.modules["lobang.scrapers._fake"] = fake
        try:
            res = S.fetch({"name": "f", "type": "scrape", "parser": "_fake", "publisher": "P"})
        finally:
            del sys.modules["lobang.scrapers._fake"]
        self.assertTrue(res["ok"])
        self.assertEqual(len(res["items"]), 1)
        it = res["items"][0]
        self.assertEqual(it["summary"], "hi")
        self.assertEqual(it["published"].utcoffset().total_seconds(), 8 * 3600)
        self.assertEqual(it["published"].hour, 9)

    def test_missing_key_source_is_skipped_not_failed(self):
        from lobang import fetch as F
        from unittest import mock
        srcs = [{"name": "a", "type": "rss", "url": "u"}, {"name": "b", "type": "api", "parser": "x", "env": "LOBANG_TEST_NOPE"}]
        os.environ.pop("LOBANG_TEST_NOPE", None)
        with mock.patch.object(F.yaml, "safe_load", return_value={"sources": srcs}):
            names = [s["name"] for s in F.load_sources()]
        self.assertEqual(names, ["a"])


class FetchWrapper(unittest.TestCase):
    def test_parser_crash_contained(self):
        src = {"name": "bad", "type": "rss", "url": "https://x"}
        orig = S.net.get
        S.net.get = lambda *a, **k: b"\x00\x01"
        try:
            res = S.fetch(src)
        finally:
            S.net.get = orig
        self.assertFalse(res["ok"])
        self.assertTrue(res["error"])


class NetRetry(unittest.TestCase):
    """2026-11-03: one 503 burst from Google News failed all 10 gnews sources at once."""

    def _run(self, outcomes):
        from lobang import net
        calls, slept = [], []

        def once(url, ua, timeout):
            calls.append(url)
            o = outcomes[len(calls) - 1]
            if isinstance(o, Exception):
                raise o
            return o

        orig = net._get_once
        net._get_once = once
        try:
            try:
                return net.get("u", sleep=slept.append), calls, slept
            except net.FetchError as exc:
                return exc, calls, slept
        finally:
            net._get_once = orig

    def test_transient_503_is_retried(self):
        from lobang import net
        res, calls, slept = self._run([net.FetchError("HTTP 503", 503, transient=True), b"ok"])
        self.assertEqual(res, b"ok")
        self.assertEqual(len(calls), 2)
        self.assertEqual(slept, [net.RETRY_DELAYS[0]])

    def test_retry_after_honoured(self):
        from lobang import net
        res, _, slept = self._run([net.FetchError("HTTP 429", 429, transient=True, wait=7), b"ok"])
        self.assertEqual(res, b"ok")
        self.assertEqual(slept, [7])

    def test_gives_up_after_last_delay(self):
        from lobang import net
        e = net.FetchError("HTTP 503", 503, transient=True)
        res, calls, _ = self._run([e] * 5)
        self.assertIsInstance(res, net.FetchError)
        self.assertEqual(len(calls), len(net.RETRY_DELAYS) + 1)

    def test_permanent_error_not_retried(self):
        from lobang import net
        res, calls, slept = self._run([net.FetchError("HTTP 404", 404), b"ok"])
        self.assertIsInstance(res, net.FetchError)
        self.assertEqual((len(calls), slept), (1, []))

    def test_status_classification(self):
        import io
        import urllib.error
        from unittest import mock
        from lobang import net
        for code, transient in ((503, True), (429, True), (403, False), (404, False)):
            err = urllib.error.HTTPError("u", code, "x", {"Retry-After": "120"}, io.BytesIO())
            with mock.patch.object(net.urllib.request, "urlopen", side_effect=err):
                with self.assertRaises(net.FetchError) as cm:
                    net._get_once("https://x", "library", 1)
            self.assertEqual(cm.exception.transient, transient, code)
            self.assertEqual(cm.exception.wait, net.RETRY_AFTER_CAP if transient else None)


class GnewsLane(unittest.TestCase):
    def test_gnews_requests_never_overlap(self):
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor
        active, peak, lock = [0], [0], threading.Lock()

        def fake_get(url, ua="browser", **kw):
            with lock:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
            time.sleep(0.02)
            with lock:
                active[0] -= 1
            return b"<rss version='2.0'><channel></channel></rss>"

        orig, gap = S.net.get, S.GNEWS_GAP
        S.net.get, S.GNEWS_GAP = fake_get, 0
        try:
            srcs = [{"name": "g%d" % i, "type": "gnews", "query": "q"} for i in range(6)]
            with ThreadPoolExecutor(max_workers=6) as pool:
                list(pool.map(S.fetch, srcs))
        finally:
            S.net.get, S.GNEWS_GAP = orig, gap
        self.assertEqual(peak[0], 1)

    def test_breaker_after_exhausted_retries(self):
        seen = []

        def fake_get(url, ua="browser", **kw):
            seen.append(kw)
            raise S.net.FetchError("HTTP 503", 503, transient=True)

        orig, gap = S.net.get, S.GNEWS_GAP
        S.net.get, S.GNEWS_GAP = fake_get, 0
        S.gnews_reset()
        try:
            res = [S.fetch({"name": "g%d" % i, "type": "gnews", "query": "q"}) for i in range(3)]
        finally:
            S.net.get, S.GNEWS_GAP = orig, gap
            S.gnews_reset()
        self.assertFalse(any(r["ok"] for r in res))
        self.assertEqual(seen[0], {})                    # first query: full retries
        self.assertEqual(seen[1]["delays"], ())          # rest: one short attempt
        self.assertEqual(seen[2]["timeout"], S.GNEWS_TRIPPED_TIMEOUT)

    def test_run_keeps_config_order(self):
        from unittest import mock
        from lobang import fetch as F
        srcs = [{"name": n, "type": t} for n, t in
                (("a", "rss"), ("g1", "gnews"), ("b", "rss"), ("g2", "gnews"))]
        order = []

        def fake_fetch(src):
            order.append(src["name"])
            return {"ok": False, "items": [], "error": src["name"]}

        with mock.patch.object(F, "load_sources", return_value=srcs), \
                mock.patch.object(F, "fetch", side_effect=fake_fetch), \
                mock.patch.object(F, "Lexicon"):
            rc = F.run(dry_run=True)
        self.assertEqual(rc, 2)                          # all failed: refuses to write
        self.assertEqual(sorted(order), ["a", "b", "g1", "g2"])


if __name__ == "__main__":
    unittest.main()
