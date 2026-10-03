"""Offline tests for lobang/scrapers/* against trimmed real pages captured 2026-10-03.

Each module is fetch(src, get, key) -> parse(body); tests call parse() on the fixture and
check a changed-markup page raises FetchError (never returns an empty "ok").
"""

import io
import os
import sys
import unittest
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lobang.net import FetchError
from lobang.scrapers import dbs_dining, hungrygowhere, misslobang
from lobang.textutil import SGT

FIX = os.path.join(ROOT, "tests", "fixtures")
CHANGED = b"<html><body><h1>We have redesigned</h1><div class='x'>nothing here</div></body></html>"


def raw(name):
    with io.open(os.path.join(FIX, name), "rb") as fh:
        return fh.read()


def check_items(tc, items, minimum=3):
    tc.assertGreaterEqual(len(items), minimum)
    for it in items:
        tc.assertTrue(it["title"].strip())
        tc.assertTrue(it["url"].startswith("https://"))
        tc.assertNotIn("<", it["title"])
        tc.assertNotIn("&amp;", it["title"])
    tc.assertEqual(len({i["url"] for i in items}), len(items))


class MissLobang(unittest.TestCase):
    NOW = datetime(2026, 10, 3, 12, 0, tzinfo=SGT)

    def test_fixture(self):
        items = misslobang.parse(raw("scrape_misslobang.html"), now=self.NOW)
        check_items(self, items)
        self.assertTrue(items[0]["url"].startswith("https://www.misslobang.com/article/"))
        self.assertIn("Molly Tea", items[0]["title"])
        self.assertIn("1-for-1", items[0]["summary"])
        dated = [i for i in items if i["published"]]
        self.assertTrue(dated and dated[0]["published"].year == 2026)

    def test_old_dated_cards_dropped(self):
        later = datetime(2027, 6, 1, tzinfo=SGT)
        items = misslobang.parse(raw("scrape_misslobang.html"), now=later)
        self.assertTrue(all(i["published"] is None for i in items))

    def test_markup_changed_raises(self):
        with self.assertRaises(FetchError):
            misslobang.parse(CHANGED)

    def test_fetch_uses_registry_url(self):
        seen = []

        def get(url, **kw):
            seen.append(url)
            return raw("scrape_misslobang.html")
        misslobang.fetch({"url": "https://www.misslobang.com/category/deals"}, get, None)
        self.assertEqual(seen, ["https://www.misslobang.com/category/deals"])


class DbsDining(unittest.TestCase):
    def test_fixture(self):
        items = dbs_dining.parse(raw("scrape_dbs_dining.html"))
        check_items(self, items)
        self.assertNotIn("?", items[0]["url"])
        self.assertIn("A Hot Hideout: S$3 off", items[0]["title"])
        self.assertTrue(all(i["published"] is None for i in items))

    def test_markup_changed_raises(self):
        with self.assertRaises(FetchError):
            dbs_dining.parse(CHANGED)


class HungryGoWhere(unittest.TestCase):
    def test_fixture(self):
        items = hungrygowhere.parse(raw("scrape_hungrygowhere.html"))
        check_items(self, items)
        self.assertTrue(all(i["published"] for i in items))
        self.assertEqual(items[0]["published"].day, 2)
        self.assertTrue(any(i["summary"] == "New Openings" for i in items))

    def test_markup_changed_raises(self):
        with self.assertRaises(FetchError):
            hungrygowhere.parse(CHANGED)


if __name__ == "__main__":
    unittest.main()
