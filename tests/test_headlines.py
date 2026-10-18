"""Every labelled headline in tests/fixtures/headlines.tsv classifies as labelled.

The file is the misfire log: a misfire found in the live feed becomes a row before its fix, so
the same mistake fails a test forever after. tools/replay.py shows what a rule change does to
every stored headline; this file pins the ones a human has judged.
"""

import os
import unittest
from datetime import date

from lobang.classify import Lexicon, classify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEX = Lexicon.load(os.path.join(ROOT, "config", "merchants.yml"))
REF = date(2026, 10, 8)
FLAGS = {"fnb", "post", "gnews", "scope"}


def rows():
    with open(os.path.join(ROOT, "tests", "fixtures", "headlines.tsv"), encoding="utf-8") as fh:
        lines = [ln.rstrip("\n") for ln in fh if ln.strip() and not ln.startswith("#")]
    head = lines[0].split("\t")
    assert head == ["expect", "flags", "title", "summary"], head
    out = []
    for n, ln in enumerate(lines[1:], 2):
        cols = ln.split("\t")
        assert len(cols) == 4, "row %d has %d columns, not 4 (tabs only)" % (n, len(cols))
        out.append(cols)
    return out


class LabelledHeadlines(unittest.TestCase):
    def test_file_is_well_formed(self):
        rs = rows()
        self.assertGreater(len(rs), 0)
        for expect, flags, title, _ in rs:
            kind, *checks = expect.split(" ")
            self.assertIn(kind, ("drop", "promo", "opening"), title)
            self.assertFalse(checks and kind == "drop", title)
            for chk in checks:
                self.assertRegex(chk, r"^[+-][\w-]+$", title)
            fl = set() if flags == "-" else set(flags.split(","))
            self.assertLessEqual(fl, FLAGS, title)
        titles = [r[2] for r in rs]
        self.assertEqual(len(titles), len(set(titles)), "duplicate title")

    def test_every_row_classifies_as_labelled(self):
        for expect, flags, title, summary in rows():
            fl = set() if flags == "-" else set(flags.split(","))
            item = {"title": title, "summary": "" if summary == "-" else summary,
                    "fnb_only": "fnb" in fl, "post_body": "post" in fl, "sg_source": "gnews" not in fl,
                    "publisher": "Fixture", "scope": "promo" if "scope" in fl else "mixed"}
            c = classify(item, LEX, REF)
            kind, *checks = expect.split(" ")
            with self.subTest(title=title):
                if kind == "drop":
                    self.assertIsNone(c, "should drop, got %s" % (c and c["kind"]))
                else:
                    self.assertIsNotNone(c, "should be %s, was dropped" % kind)
                    self.assertEqual(c["kind"], kind)
                    for chk in checks:
                        if chk[0] == "+":
                            self.assertIn(chk[1:], c["tags"])
                        else:
                            self.assertNotIn(chk[1:], c["tags"])


if __name__ == "__main__":
    unittest.main()
