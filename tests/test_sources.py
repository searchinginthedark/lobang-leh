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


if __name__ == "__main__":
    unittest.main()
