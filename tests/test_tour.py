"""The guided tour must follow the user flow (the user's rule, 2026-10-03): any change to what
a user can tap or see as a view has to update the tour steps in public/index.html.

FLOW below pins every user-facing control. When a test here fails after a UI change:
  1. update the <li> steps in public/index.html #tour-steps so they describe the new flow,
  2. then update FLOW / the label lists below to match.
Never update FLOW alone; that is exactly the drift this file exists to stop.
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as fh:
        return fh.read()


HTML = read("public", "index.html")
JS = read("public", "app.js")

# Every control a user can reach: ids of buttons/inputs/selects in the page, the views, and the
# classes of buttons app.js builds per card or list.
FLOW = {
    "page": {"tourbtn", "refresh", "q", "t-1for1", "t-free", "clear", "bday-m", "bday-d"},
    "views": {"hot", "ending", "new", "birthday", "saved"},
    "js_buttons": {"summary-btn", "more-btn", "act", "show-more", "chip", "icon-btn"},
}
# Labels the tour text must mention, so a renamed tab or filter cannot slip past it.
MUST_MENTION = ["Hot", "Ending soon", "New openings", "Birthday", "Saved", "1-for-1", "Free", "Clear filters",
                "Show more", "Save", "Share", "PROMO", "NEW OPENING", "+3"]


def tour_block():
    m = re.search(r'<div class="tour" id="tour"([^>]*)>(.*?)</ol>\s*</div>', HTML, re.S)
    assert m, "tour markup missing"
    return m


def steps():
    ol = re.search(r'<ol id="tour-steps"([^>]*)>(.*?)</ol>', HTML, re.S)
    return ol, re.findall(r'<li data-target="([^"]*)" data-view="([^"]*)"><b>([^<]+)</b><span>([^<]+)</span></li>',
                          ol.group(2))


class TourMarkup(unittest.TestCase):
    def test_ships_hidden_with_dialog_semantics(self):
        m = tour_block()
        self.assertIn(" hidden", m.group(1))
        for attr in ('role="dialog"', 'aria-modal="true"', 'aria-labelledby="tour-t"'):
            self.assertIn(attr, m.group(1))
        self.assertIn('<input type="checkbox" id="tour-off"> Do not show again', m.group(2))
        for bid in ("tour-skip", "tour-back", "tour-next"):
            self.assertIn('id="%s"' % bid, m.group(2))
        self.assertRegex(HTML, r'<button[^>]*id="tourbtn"[^>]*hidden')

    def test_steps_are_short_and_bookended(self):
        ol, st = steps()
        self.assertIn(" hidden", ol.group(1))
        self.assertGreaterEqual(len(st), 4)
        self.assertLessEqual(len(st), 8, "a tour people finish is short")
        self.assertEqual(st[0][0], "", "first step is the centred welcome")
        self.assertEqual(st[-1][0], "tourbtn", "last step shows how to replay")

    def test_every_target_exists(self):
        page_ids = set(re.findall(r'\bid="([^"]+)"', HTML))
        for target, view, title, _ in steps()[1]:
            if not target:
                continue
            # A list target is assigned by app.js at render time.
            self.assertTrue(target in page_ids or ("'%s'" % target) in JS,
                            "tour step '%s' points at a missing id: %s" % (title, target))
            if view:
                self.assertIn(view, FLOW["views"])


class TourFollowsFlow(unittest.TestCase):
    """Fails on any user-flow change until the tour steps (and then FLOW) are updated."""

    def test_page_controls_pinned(self):
        found = set(re.findall(r'<(?:button|input|select)[^>]*\bid="([^"]+)"', HTML))
        found -= {"tour-off", "tour-skip", "tour-back", "tour-next"}
        self.assertEqual(found, FLOW["page"], "page controls changed: update the tour steps, then FLOW")

    def test_views_pinned(self):
        tabs = set(re.findall(r'data-view="(\w+)" aria-selected', HTML))
        js = set(re.findall(r"'(\w+)'", re.search(r"var VIEWS = \[([^\]]*)\]", JS).group(1)))
        self.assertEqual(tabs, FLOW["views"], "tabs changed: update the tour steps, then FLOW")
        self.assertEqual(js, FLOW["views"])

    def test_js_built_buttons_pinned(self):
        found = set(re.findall(r"el\('button', '([\w-]+)", JS))
        self.assertEqual(found, FLOW["js_buttons"], "card/list buttons changed: update the tour steps, then FLOW")

    def test_tour_text_names_every_control(self):
        text = " ".join(t + " " + b for _, _, t, b in steps()[1])
        for label in MUST_MENTION:
            self.assertIn(label, text, "tour never mentions '%s'" % label)
        # The labels it names must still be real UI text.
        for label in ("Hot", "Ending soon", "New openings", "Birthday", "Saved", "1-for-1", "Free", "Clear filters"):
            self.assertIn(">" + label + "<", HTML, "tour names '%s' but the page no longer shows it" % label)
        for label in ("Show ", "'Save'", "'Share'", "'New opening'", "'Promo'"):
            self.assertIn(label, JS)


if __name__ == "__main__":
    unittest.main()
