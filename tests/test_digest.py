import os
import shutil
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lobang import digest as G
from lobang.textutil import SGT, iso

NOW = datetime(2026, 10, 22, 8, 1, tzinfo=SGT)


def deal(i, hours_ago, **kw):
    d = {"id": "d%d" % i, "title": "Deal %d 1-for-1" % i, "tags": [], "first_seen": iso(NOW - timedelta(hours=hours_ago))}
    d.update(kw)
    return d


class Pick(unittest.TestCase):
    def test_top_three_new_in_hot_order(self):
        ds = [deal(1, 2), deal(2, 30), deal(3, 5), deal(4, 23), deal(5, 1)]
        self.assertEqual([d["id"] for d in G.pick(ds, NOW)], ["d1", "d3", "d4"])

    def test_skips_birthday_and_unconfirmed(self):
        ds = [deal(1, 2, tags=["birthday"]), deal(2, 2, unconfirmed=True), deal(3, 2)]
        self.assertEqual([d["id"] for d in G.pick(ds, NOW)], ["d3"])

    def test_nothing_new_sends_nothing(self):
        self.assertIsNone(G.payload(G.pick([deal(1, 48)], NOW), NOW))

    def test_payload_shape(self):
        p = G.payload([deal(1, 1), deal(2, 1)], NOW)
        self.assertEqual(p["day"], "2026-10-22")
        self.assertEqual(p["title"], "2 new lobangs today")
        self.assertEqual(p["body"].count("\n"), 1)
        self.assertEqual(G.payload([deal(1, 1)], NOW)["title"], "1 new lobang today")

    def test_send_window(self):
        at = lambda h, m=0: datetime(2026, 10, 22, h, m, tzinfo=SGT)
        self.assertFalse(G.in_window(at(7, 59)))
        self.assertTrue(G.in_window(at(8, 0)))
        self.assertTrue(G.in_window(at(12, 59)))
        self.assertFalse(G.in_window(at(13, 0)))
        self.assertFalse(G.in_window(at(21)))
        # 00:00Z is 08:00 SGT: the cron-job.org morning collect lands inside the window.
        self.assertTrue(G.in_window(datetime(2026, 10, 22, 0, 1, tzinfo=timezone.utc)))
        self.assertFalse(G.in_window(datetime(2026, 10, 22, 13, 0, tzinfo=timezone.utc)))   # 21:00 SGT


@unittest.skipUnless(shutil.which("node"), "node not installed")
class DigestApi(unittest.TestCase):
    """api/_digest.js: auth, the per-day lock, pruning dead subscriptions (tests/digest_api.js)."""

    def test_node_suite(self):
        out = subprocess.run(["node", os.path.join(ROOT, "tests", "digest_api.js")],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)


if __name__ == "__main__":
    unittest.main()
