"""lobang.attrs: what a deal asks of the reader, and how that moves it in Hot.

Each case is a real post (live feed, 2026-10-18) or its near-miss. The near-misses matter most:
every one of them fired a need on the first draft of these rules.
"""

import os
import re
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lobang import attrs as A  # noqa: E402
from lobang import deals as D  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (headline, post text, tags, needs that MUST be found, needs that must NOT be)
CASES = [
    # --- stated needs ---
    ("LiHo: Free bubble tea", "Get a drink for free on your birthday with LiHo; all you've got to do is register for a "
     "free LiHo's membership via the LiHo TEA app.", ["free", "birthday"], {"member", "app"}, set()),
    ("Jumbo Seafood: $100 birthday voucher with min. $200 spent", "Sign up as a Jumbo Rewards member and you'll receive "
     "a $100 voucher with a minimum spend of $200.", [], {"member", "min-spend"}, set()),
    ("CLOVE Korean Buffet at Swissôtel: 50% Off With 9 Bank Cards, Weekday Lunch $40++", "Cards from OCBC, DBS/POSB, "
     "Citibank, HSBC, Maybank, UOB.", ["pct-off", "card"], {"card"}, set()),
    ("Sinpopo Brand: 1-for-1 Mains", "Sinpopo Brand: 1-for-1 Mains 🦑 / Bring along a lunch buddy & enjoy 1-for-1 mains / "
     "Simply quote <1FOR1> when making a reservation to redeem / Now till 30 Oct (Weekdays) / 11AM - 12PM / Tangs",
     ["1-for-1"], {"code", "booking", "days", "hours"}, {"purchase"}),
    ("Hippopotato – Ex-Marche chef & sibling open 1st physical rosti store", "The usual price is S$8, but to celebrate "
     "their grand opening, the first 50 customers can get it for S$5.", [], {"first-n"}, set()),
    ("Starbucks: Free slice of cake with any drink purchased", "If you frequent Starbucks often, you would know about "
     "this freebie, which lands on your birthday every year without fail.", ["free"], {"purchase"}, set()),
    ("McDonald's Free 4pc Chicken McNuggets With Any Double McSpicy or Double Bulgogi Meal, 15 Oct to 4 Nov 2026",
     "McDonald's Singapore is throwing in a free 4pc Chicken McNuggets with four double-patty meals from Thursday.",
     ["free"], {"purchase"}, set()),
    ("ChaPanda: 1-for-1 Oolong Milk Tea", "Enjoy two large cups of fragrant Oolong Milk Tea for only $6.50 / "
     "Every Mon & Tue / 10AM - 10PM / Century Square, #01-36", ["1-for-1"], {"days"}, {"hours", "purchase"}),
    ("Win a year of free pizza!", "Follow us on Instagram, like and share this post, and tag 3 friends to stand a "
     "chance to win. Winners will be announced on 1 Nov.", ["free"], {"contest", "social"}, set()),
    ("Collin's $8.80 Student Meal: Every Day at 5 Restaurants", "Students only: show your student card at the counter "
     "to get the set meal at $8.80 at five outlets.", [], {"eligible"}, set()),
    ("Family Hakata – Halal mookata for just $19.90", "Family Hakata offers a S$19.90 per pax deal for a minimum of 2 "
     "people, covering seafood, marinated meats and more.", [], {"group"}, set()),
    # --- near-misses: each fired on a first draft ---
    ("IKEA S'pore Offers FREE Coffee or Tea at Swedish Restaurants from 19 – 23 Oct 2026", "Enjoy a complimentary hot "
     "drink and a cosy break at IKEA, with no minimum spend required, all week long at both stores.",
     ["free"], set(), {"min-spend", "purchase"}),
    ("Peach Garden À La Carte Buffet at The Metropolis: From $30++", "The ++ adds about 20%, and it cannot be combined "
     "with credit card or membership deals, so plan for the full price at every table.", [], set(), {"card", "member"}),
    ("Genki Sushi x Crayon Shinchan: Cheesy Ebi Fry Taco $3.20", "The bag is $10.90, or $7.90 with a DBS/POSB card, and "
     "Genki's free app membership pays for itself on the lunch bag alone.", ["cheap"], set(), {"card", "member"}),
    ("15 HOT WINGS FOR $25?! WEDNESDAY JUST GOT SPICY", "Get 15 Hot Wing pieces for just $25 / Pick from French Fries "
     "or Coleslaw / Order via the KFC App or grab it in-store / KFC Singapore", [], set(), {"app"}),
    ("Sushiro adds three premium plates until 3 November, from S$3.90++", "Sushiro Singapore prices the Aburi Wild "
     "Blackthroat Seaperch at S$3.90++ and Bancha Braised Octopus at S$3.90++, while stocks last.",
     ["cheap"], set(), {"first-n"}),
    ("PlayMade's Protein Smoothie Series: From $6.90", "A limited-time line at all 28 stores, which also brings $4.90 "
     "crew socks and a $39.90 bottle with any drink, in three medium iced smoothies.", [], set(), {"purchase"}),
    ("KFC Chicken Tuesday: 5 Pieces for $10.95", "Choose between 5 pieces of the Original Recipe or Hot & Crispy Chicken "
     "for only $10.95 / Limited to 2 sets per transaction for dine-in & takeaway orders", [], {"days"}, {"first-n"}),
    ("CLOVE Korean Buffet: Weekday Lunch $40++", "The weekday lunch buffet is $40++ and dinner is $58++ every night, "
     "with lobster kimchi stew on weekends and a dessert bar at every session.", [], set(), {"days"}),
]


def run(case):
    title, text, tags, _, _ = case
    return A.extract(title, text, tags)


class Needs(unittest.TestCase):
    def test_cases(self):
        for case in CASES:
            got = set(run(case)["needs"])
            self.assertTrue(case[3] <= got, "%s: missing %s (got %s)" % (case[0][:50], case[3] - got, got))
            self.assertFalse(case[4] & got, "%s: should not need %s" % (case[0][:50], case[4] & got))

    def test_min_spend_amount(self):
        a = A.extract("Famous Amos: Free cookie gift", "Get a free bag of cookies with a min. spend of $5 in your "
                      "birthday month, at any outlet islandwide.", ["free"])
        self.assertEqual(a["min_spend"], 5)

    def test_one_day_from_dates(self):
        a = A.extract("Mr Bean 1-for-1 soy drinks", "Almost all soy drinks are 1-for-1 at every outlet this "
                      "Sunday, from opening to closing time.", ["1-for-1"], valid=("2026-10-18", "2026-10-18"))
        self.assertIn("one-day", a["needs"])

    def test_birthday_needs_carry_over(self):
        a = A.extract("Brand: Free cake", "", ["free", "birthday"], {"needs": ["member", "booking"], "min_spend": 50})
        self.assertTrue({"member", "booking", "min-spend"} <= set(a["needs"]))
        self.assertEqual(a["min_spend"], 50)

    def test_needs_keep_display_order(self):
        got = run(CASES[3])["needs"]
        self.assertEqual(got, [n for n in A.NEEDS if n in got])


class Cost(unittest.TestCase):
    def test_buy_one_get_one_free_is_a_one_for_one(self):
        a = A.extract("Sheng Siong Housebrand Buy-1-Get-1-FREE Frozen Deals", "Enjoy 1-for-1 frozen favourites "
                      "and save on PWP household essentials across all stores.", ["free", "1-for-1"])
        self.assertEqual(a["cost"], "1-for-1")

    def test_body_freebie_is_not_the_deal(self):
        a = A.extract("Cold Storage International Wine Fair 2026: Extra 15% Off 6 Bottles", "Any 6 bottles get an "
                      "additional 15% off, with free wine tastings on Friday to Sunday.", ["free", "pct-off"], pct=15)
        self.assertEqual(a["cost"], "pct-off")


class Ease(unittest.TestCase):
    def test_unknown_is_not_easy(self):
        a = A.extract("Brand 1-for-1 coffee", "", ["1-for-1"])
        self.assertFalse(a["checked"])
        self.assertEqual(A.ease_points(a), 0)
        self.assertFalse(A.is_easy(a))

    def test_boilerplate_is_not_text(self):
        a = A.extract("Popeyes Truffle Chicken from $8", "Your usual Popeyes order just got a little more atas. "
                      "Visit Great Deals Singapore for the full post.", [])
        self.assertFalse(a["checked"])

    def test_walk_in_freebie_beats_card_deal(self):
        walk = A.extract(*CASES[11][:3])
        card = A.extract(*CASES[2][:3])
        self.assertGreater(A.ease_points(walk), A.ease_points(card))
        self.assertTrue(A.is_easy(walk))

    def test_freebie_with_purchase_gets_no_freebie_bonus(self):
        a = run(CASES[6])
        self.assertLessEqual(A.ease_points(a), 8)

    def test_contest_is_never_easy(self):
        a = run(CASES[8])
        self.assertFalse(A.is_easy(a))
        self.assertLess(A.ease_points(a), -15)

    def test_page_threshold_matches(self):
        with open(os.path.join(ROOT, "public", "app.js"), encoding="utf-8") as fh:
            js = fh.read()
        self.assertEqual(int(re.search(r"var EASY_MIN = (\d+);", js).group(1)), A.EASY_MIN)
        for n in A.NEEDS:
            self.assertIn("'%s':" % n, js, "app.js NEED_LABEL lacks %s" % n)


class HotOrder(unittest.TestCase):
    def deal(self, title, body, tags):
        return {"kind": "promo", "title": title, "summary": body[:280], "body": body, "tags": tags, "pct": None,
                "merchants": ["X"], "publishers": 1, "best_tier": "deals", "famous": False,
                "published": "2026-10-18T09:00:00+08:00", "valid_until": None, "valid_from": None}

    def test_easier_deal_scores_higher(self):
        today = date(2026, 10, 18)
        easy = self.deal("X: Free coffee", "Walk in to any outlet and ask for a free coffee, no purchase needed, "
                         "all day on every day this week.", ["free"])
        hard = self.deal("X: Free coffee", "Free coffee for DBS cardholders only, with a minimum spend of $30 via the "
                         "X app, while you sign up as a member at the counter.", ["free"])
        self.assertGreater(D.score(easy, today), D.score(hard, today) + 15)


class PublicCard(unittest.TestCase):
    def state_deal(self, body, tags):
        m = {"title": "IKEA S'pore Offers FREE Coffee or Tea", "summary": body[:600], "tier": "deals",
             "publisher": "SingPromos", "url": "https://x/1", "fetched": "2026-10-18T09:00:00+08:00",
             "published": "2026-10-18T08:00:00+08:00", "id": "a",
             "cls": {"kind": "promo", "merchants": ["IKEA"], "tags": tags, "category": "cafe", "origin": None}}
        return D.aggregate({"id": "d_x", "members": [m]})

    def test_loose_member_tag_follows_the_strict_reader(self):
        d = self.state_deal("Enjoy a complimentary hot drink at IKEA, no minimum spend required, for Family members "
                            "and everyone else at both stores this week. [", ["free", "member"])
        pub = D.public(d, date(2026, 10, 18))
        self.assertNotIn("member", pub["tags"])
        self.assertEqual(pub["attrs"]["needs"], [])

    def test_member_tag_kept_when_the_post_requires_it(self):
        d = self.state_deal("Free coffee for IKEA Family members only: sign up as a member at the counter first, "
                            "then show the app at any Swedish Restaurant.", ["free", "member"])
        self.assertIn("member", D.public(d, date(2026, 10, 18))["tags"])

    def test_stored_read_more_marker_is_tidied(self):
        d = self.state_deal("Enjoy a complimentary hot drink and a cosy break at IKEA, with no minimum spend "
                            "required. [", ["free"])
        self.assertFalse(d["summary"].endswith("["))
        self.assertFalse(d["body"].endswith("["))


class FullText(unittest.TestCase):
    def test_paragraphs_survive_and_markup_does_not(self):
        from lobang.textutil import body_text
        html = ("<p>First para &amp; more.</p><script>var x = 1;</script><figure><img src=a>"
                "<figcaption>Photo: Brand</figcaption></figure><ul><li>One</li><li>Two</li></ul>"
                "<p>The post X appeared first on Eatbook.</p>")
        self.assertEqual(body_text(html).split("\n"), ["First para & more.", "Photo: Brand", "• One", "• Two"])

    def test_clipped_at_a_paragraph_with_a_marker(self):
        from lobang.textutil import body_text
        out = body_text("<p>" + "a" * 60 + "</p><p>" + "b" * 60 + "</p>", n=100)
        self.assertEqual(out.split("\n"), ["a" * 60, "…"])

    def test_body_never_reaches_the_classifier(self):
        from lobang import sources as S
        src = {"name": "t", "type": "rss", "publisher": "T"}
        it = S._item(src, "New cafe menu at Funan", "https://x/2", "A short excerpt.", None,
                     body="<p>A short excerpt.</p><p>1-for-1 on everything, free drinks for all!</p>")
        self.assertEqual(it["summary"], "A short excerpt.")
        self.assertIn("1-for-1", it["body"])

    def test_no_body_kept_when_it_adds_nothing(self):
        from lobang import sources as S
        it = S._item({"name": "t", "type": "rss"}, "KFC deal", "https://x/3", "<p>Same text.</p>", None)
        self.assertNotIn("body", it)


if __name__ == "__main__":
    unittest.main()
