"""The feature map (features.json) must cover every control a user can reach.

features.json is what an agent reads to learn how the app works and what
../memory/tools/verify/verify.py drives to prove each feature still works. A map that
misses a control silently leaves it unverified, so a new button, input or view fails
here until a feature that reaches it is added to the map.
"""

import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as fh:
        return fh.read()


HTML = read("public", "index.html")
MAP = json.loads(read("features.json"))
BLOB = json.dumps(MAP["features"])


class FeatureMap(unittest.TestCase):
    def test_every_control_is_mapped(self):
        ids = set(re.findall(r'<(?:button|input|select|textarea|a)\b[^>]*\bid="([^"]+)"', HTML))
        missing = sorted(i for i in ids - set(MAP.get("ignore_controls", [])) if i not in BLOB)
        self.assertEqual(missing, [], "controls with no feature in features.json")

    def test_every_view_is_mapped(self):
        views = set(re.findall(r'data-view="([a-z]+)"', HTML))
        missing = sorted(v for v in views if 'data-view=%s' % v not in BLOB)
        self.assertEqual(missing, [], "views with no feature in features.json")

    def test_features_are_complete(self):
        seen = set()
        for f in MAP["features"]:
            for k in ("id", "name", "reach", "expect"):
                self.assertIn(k, f, "feature %r lacks %r" % (f.get("id"), k))
            self.assertNotIn(f["id"], seen, "duplicate feature id")
            seen.add(f["id"])
            self.assertTrue(f["expect"], "feature %r proves nothing" % f["id"])


if __name__ == "__main__":
    unittest.main()
