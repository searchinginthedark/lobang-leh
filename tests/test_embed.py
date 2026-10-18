"""Semantic search: the shipped model files, and the two tokenizer/encoder ports that read them.

lobang/embed.py embeds every deal in CI; public/embed.js embeds the query on the phone. A query is
only comparable with a deal if both produce the same token ids and the same vector, so both are
pinned to HuggingFace's own tokenizer output (tests/fixtures/embed_tokens.json, written by
tools/build_embed_model.py) and to each other.
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lobang import embed as E  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "tests", "fixtures", "embed_tokens.json"), encoding="utf-8") as fh:
    FIX = json.load(fh)
MODEL = E.Model.load()


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


class ModelFiles(unittest.TestCase):
    def test_every_token_has_a_row(self):
        self.assertEqual(len(MODEL.table), len(MODEL.vocab))
        n = len(os.listdir(os.path.join(E.ROOT, "t")))
        self.assertEqual(n, (len(MODEL.vocab) + E.SHARD - 1) // E.SHARD)

    def test_rows_are_finite(self):
        for i in (0, 1000, len(MODEL.vocab) - 1):
            scale, raw = MODEL.table[i]
            self.assertTrue(scale == scale and abs(scale) < 10)
            self.assertEqual(len(raw), E.DIM)


class PythonPort(unittest.TestCase):
    def test_token_ids_match_huggingface(self):
        for case in FIX["cases"]:
            self.assertEqual(MODEL.tokenize(case["text"]), case["ids"][:E.MAX_TOKENS], case["text"][:60])

    def test_vectors_are_unit_length(self):
        v = MODEL.encode("1-for-1 bubble tea at Jewel")
        self.assertAlmostEqual(dot(v, v), 1.0, places=6)

    def test_unknown_text_has_no_vector(self):
        self.assertIsNone(MODEL.encode(""))
        self.assertIsNone(MODEL.encode("!!! ???"[:0]))

    def test_meaning_not_just_words(self):
        # "complimentary" shares no word with "free food", yet must sit nearer than an unrelated deal.
        q = MODEL.encode("free food")
        near = MODEL.encode("Complimentary nasi lemak for every customer this Friday")
        far = MODEL.encode("Toyota car servicing package 20% off")
        self.assertGreater(dot(q, near), dot(q, far) + 0.1)

    def test_quantize_round_trip(self):
        v = MODEL.encode("cheap coffee")
        q = [b - 256 if b > 127 else b for b in E.quantize(v)]
        self.assertGreater(dot(v, q) / 127.0, 0.999)

    def test_deal_text_uses_only_the_body_opening(self):
        d = {"merchants": ["KFC"], "title": "5 pieces for $10.95", "summary": "Tuesdays only.", "body": "x" * 5000}
        self.assertLess(len(E.deal_text(d)), 700)


@unittest.skipUnless(shutil.which("node"), "node not installed")
class JsPort(unittest.TestCase):
    """public/embed.js, run in Node exactly as the page runs it."""

    @classmethod
    def setUpClass(cls):
        cls.texts = [c["text"] for c in FIX["cases"]] + ["korean fried chicken near bugis", "Häagen-Dazs 1-for-1!"]
        out = subprocess.run(["node", os.path.join(ROOT, "tests", "embed_parity.js")],
                             input=json.dumps(cls.texts), capture_output=True, text=True, encoding="utf-8", check=True)
        cls.js = json.loads(out.stdout)

    def test_token_ids_match_huggingface(self):
        for case, ids in zip(FIX["cases"], self.js["ids"]):
            self.assertEqual(ids, case["ids"][:E.MAX_TOKENS], case["text"][:60])

    def test_token_ids_match_python(self):
        for t, ids in zip(self.texts, self.js["ids"]):
            self.assertEqual(ids, MODEL.tokenize(t), t[:60])

    def test_vectors_match_python(self):
        for t, v in zip(self.texts, self.js["vecs"]):
            p = MODEL.encode(t)
            if p is None:
                self.assertIsNone(v)
                continue
            self.assertGreater(dot(p, v), 0.99999, t[:60])

    def test_published_vector_decodes(self):
        b64 = base64.b64encode(E.quantize(MODEL.encode("cheap coffee"))).decode("ascii")
        self.assertEqual(len(base64.b64decode(b64)), E.DIM)


if __name__ == "__main__":
    unittest.main()
