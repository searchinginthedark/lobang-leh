"""Customer birthday perks: detection and the redemption window. Every string here is real
wording from live sources on 2026-10-03 (TheSmartLocal's "Redeem on:" lines, Miss Lobang,
Google News), unless marked otherwise.
"""

import os
import sys
import unittest
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lobang import birthday as BD
from lobang import deals as D
from lobang.textutil import SGT

from test_core import LEX, cls, item  # noqa: E402

T0 = datetime(2026, 10, 3, 9, 0, tzinfo=SGT)


def win(redeem=None, title="X: Free drink", summary=""):
    b = BD.extract(title, summary, redeem)
    return b["window"], b["before"], b["after"]


class NotYourBirthday(unittest.TestCase):
    """A brand's birthday is an ordinary promo, never a birthday perk."""

    def test_founder_birthday(self):
        c = cls("Penang Culture's Big Boss Birthday: Four New Dishes at $8.80++ Each, 1-31 Oct 2026",
                "Penang Culture is celebrating its founder's birthday with four new dishes at $8.80++ each")
        self.assertNotIn("birthday", c["tags"])
        self.assertEqual(c["valid_until"], "2026-10-31")

    def test_brand_turns_35(self):
        c = cls("Soup Restaurant Turns 35: Samsui Ginger Chicken 35% Off, Mon 14 to Fri 18 Sep 2026",
                "Soup Restaurant is marking its 35th birthday with 35% off its Signature Samsui Ginger Chicken")
        self.assertNotIn("birthday", c["tags"])

    def test_birthday_bash_and_menus(self):
        self.assertFalse(BD.is_customer("Kris+ Birthday Bash: Boosted miles, 50% off deals & more"))
        self.assertFalse(BD.is_customer("Fat Cow at 15, Monti at 10: Singapore's 2026 birthday menus"))

    def test_review_that_mentions_a_birthday(self):
        # Made up: a cue with no perk beside it.
        self.assertFalse(BD.is_customer("New omakase in Tanjong Pagar",
                                        "A good spot to celebrate your birthday with friends."))


class YourBirthday(unittest.TestCase):
    def test_headline_cues(self):
        for t in ("Free bubble tea on your birthday at LiHO",
                  "McDonald's: free 20-pc McNuggets in your birthday month",
                  "Haidilao birthday perks: free fruit platter for celebrants"):
            self.assertTrue(BD.is_customer(t), t)

    def test_excerpt_cue_needs_a_perk(self):
        self.assertTrue(BD.is_customer("Cedele rewards", "redeem a free slice of cake during your birthday month"))

    def test_birthday_perk_is_a_tagged_promo(self):
        c = cls("Jumbo Seafood: $100 birthday voucher with min. $200 spent")
        self.assertEqual(c["kind"], "promo")
        self.assertIn("birthday", c["tags"])
        self.assertEqual(c["birthday"]["min_spend"], 200)

    def test_blackout_dates_in_prose_are_not_an_end_date(self):
        c = classify_roundup("Lawry's The Prime Rib: Free dessert, instant photo & 3rd main course",
                             "Join as a Lawry's Privilege Circle Member for free.",
                             "Birthday month, except December, PH, and PH eve, and 21st-31st December.")
        self.assertIsNone(c["valid_until"])
        self.assertEqual(c["birthday"]["window"], "month")
        self.assertTrue(c["birthday"]["excl_ph"])


def classify_roundup(title, summary, redeem):
    from lobang.classify import classify
    from datetime import date
    return classify({"title": title, "summary": summary, "redeem": redeem, "birthday_only": True,
                     "sg_source": True, "publisher": "TheSmartLocal", "scope": "promo"}, LEX, date(2026, 10, 3))


class Window(unittest.TestCase):
    """(a) the day only, (b) days before and/or after, (c) the whole month, and the rest."""

    def test_labelled_lines(self):
        cases = {
            "Day of dining in.": ("visit", 0, 0),
            "Up to 14 days before or after birthday.": ("around", 14, 14),
            "14 days before & after birthday.": ("around", 14, 14),
            "1 day before or after birthday.": ("around", 1, 1),
            "Within birthday month.": ("month", 0, 0),
            "WIthin birthday month.": ("month", 0, 0),
            "Within birthday month, on Mon-Thu, except PH and PH eve.": ("month", 0, 0),
            "Within 30 days of birthday month.": ("month-plus", 0, 30),
            "Within 31 days of birthday month.": ("month-plus", 0, 31),
            "On birthday.": ("day", 0, 0),
        }
        for line, want in cases.items():
            self.assertEqual(win(line), want, line)

    def test_prose_windows(self):
        self.assertEqual(win(summary="a free scoop on your birthday and the four weeks after"), ("around", 0, 28))
        self.assertEqual(win(summary="valid within 7 days of your birthday"), ("around", 7, 7))
        self.assertEqual(win(summary="a complimentary sundae on your actual birthday"), ("day", 0, 0))
        self.assertEqual(win(summary="12pm to 11:55pm in your birthday month"), ("month", 0, 0))
        self.assertEqual(win(summary="enjoy 20% off during your birthday week"), ("week", 0, 0))

    def test_loose_on_your_birthday_is_unknown(self):
        # Mr. Coconut and LiHO say this in prose and "Within birthday month" in their redeem line.
        self.assertEqual(win(summary="entitled to a free drink on their birthday"), ("unknown", 0, 0))
        self.assertEqual(win(summary="Quench your bubble tea cravings for free on your birthday"), ("unknown", 0, 0))

    def test_labelled_line_beats_prose(self):
        self.assertEqual(win("Within birthday month.", summary="a free drink on your actual birthday"),
                         ("month", 0, 0))

    def test_no_window_stated(self):
        self.assertEqual(win(None, summary="Join the rewards club for a birthday treat."), ("unknown", 0, 0))

    def test_said_quotes_the_source(self):
        b = BD.extract("X: Free", "", "Within birthday month, on Mon-Thu, except PH and PH eve.")
        self.assertEqual(b["said"], "Within birthday month, on Mon-Thu, except PH and PH eve.")
        self.assertEqual(b["days"], "Mon-Thu")
        self.assertTrue(b["excl_ph"])

    def test_month_is_not_monday(self):
        b = BD.extract("X: Free", "", "Birthday month to thursday's end")   # made up
        self.assertIsNone(b["days"])


class Conditions(unittest.TestCase):
    def test_group_counts_the_birthday_person(self):
        self.assertEqual(BD.extract("Suki-Ya: Free buffet with 3 paying adults")["group"], 4)
        self.assertEqual(BD.extract("X", "you need at least 4 people dining")["group"], 4)
        self.assertEqual(BD.extract("X", "at least 3 other adults paying for the buffet")["group"], 4)

    def test_membership_negation(self):
        self.assertNotIn("member", BD.extract("Haidilao", "you don't even need a membership")["needs"])
        self.assertNotIn("member", BD.extract("Cajun", "No membership is required, but book ahead")["needs"])
        self.assertIn("member", BD.extract("Cedele", "part of their Cedele rewards programme")["needs"])
        self.assertNotIn("member", BD.extract("X", "Remember to ask the staff")["needs"])

    def test_min_spend_from_headline_only(self):
        self.assertEqual(BD.extract("McDonald's: Free 20-piece McNuggets with $12 spent")["min_spend"], 12)
        b = BD.extract("Cedele: Free slice of cake with any drink purchase",
                       "You'll also receive a 15% off online voucher for a minimum spend of $80.")
        self.assertIsNone(b["min_spend"])

    def test_signup_lead_time(self):
        self.assertEqual(BD.extract("X", "sign up at least 2 weeks before your birthday")["signup_days"], 14)

    def test_haidilao_tag_follows_negation(self):
        c = classify_roundup("Haidilao: Free fruit platter & cake with a birthday song",
                             "The best thing is, you don't even need a membership", "Day of dining in.")
        self.assertNotIn("member", c["tags"])


class Clustering(unittest.TestCase):
    def test_birthday_perk_never_merges_with_a_promo(self):
        a = item(1, "McDonald's free 20-pc McNuggets in your birthday month", "A", T0)
        b = item(2, "McDonald's free McNuggets with any purchase", "B", T0)
        self.assertIn("birthday", a["cls"]["tags"])
        self.assertEqual(len(D.assign([a, b], [])), 2)

    def test_stated_window_wins_in_aggregate(self):
        a = item(1, "LiHO free bubble tea on your birthday", "A", T0, tier="deals")
        b = item(2, "LiHO birthday treat: free bubble tea within your birthday month", "B", T0, tier="media")
        deals = D.assign([a, b], [])
        self.assertEqual(len(deals), 1)
        self.assertEqual(deals[0]["birthday"]["window"], "month")
        self.assertEqual(D.public(deals[0], T0.date())["birthday"]["window"], "month")


if __name__ == "__main__":
    unittest.main()
