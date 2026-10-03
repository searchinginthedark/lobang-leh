import os
import sys
import unittest
from datetime import date, datetime
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lobang import deals as D
from lobang import fetch as F
from lobang.classify import Lexicon, classify, extract_validity, fold
from lobang.textutil import SGT, iso

LEX = Lexicon.load(os.path.join(ROOT, "config", "merchants.yml"))
REF = date(2026, 10, 3)   # a Saturday


def cls(title, summary="", fnb_only=False, sg_source=True, publisher="X", scope="mixed"):
    return classify({"title": title, "summary": summary, "fnb_only": fnb_only, "sg_source": sg_source,
                     "publisher": publisher, "scope": scope}, LEX, REF)


class LiveRegressions(unittest.TestCase):
    """Each case is a real headline from the 2026-10-03 audit of 29 live sources."""

    def test_gnews_foreign_opening_dropped(self):
        self.assertIsNone(cls("Seattle's New Restaurant Openings", sg_source=False, publisher="Eater Seattle"))
        self.assertIsNone(cls("Chick-fil-A Announces New Spokane Restaurant, Opening Oct. 8",
                              sg_source=False, publisher="QSR Magazine"))

    def test_gnews_sg_publisher_kept(self):
        c = cls("Viral Japanese bakery I'm Donut? to open outlet", sg_source=False, publisher="Mothership.sg")
        self.assertEqual(c["kind"], "opening")

    def test_foreign_place_dropped_even_from_sg_publisher(self):
        self.assertIsNone(cls("Horizon Mall Opens In JB With 13 F&B Brands"))
        self.assertIsNone(cls("15 New JB Cafes To Visit In 2026: Free Boardgames And More"))

    def test_foreign_city_as_origin_kept(self):
        self.assertIsNotNone(cls("Famous Tokyo bakery opens first outlet in Singapore"))

    def test_excerpt_landmark_is_not_the_merchant(self):
        c = cls("Japanese Hamburg Chain Opens First SG Outlet In CBD", "Near Lau Pa Sat in Raffles Place",
                fnb_only=True)
        self.assertEqual(c["merchants"], [])

    def test_menu_debut_is_not_first_in_sg(self):
        c = cls("Starbucks Singapore Debuts Protein Cold Foam For Coffee And Matcha Drinks")
        self.assertTrue(c is None or "first-in-sg" not in c["tags"])

    def test_non_food_product_vetoed_even_from_food_only_source(self):
        for t in ("6 Best Bedsheet Brands in Singapore (2026): Queen Sheet Prices and Promos Compared",
                  "The Brick Shop LEGO October Special: Free Astro Bot at $215, 25% Off Helicarrier, 1-31 Oct 2026",
                  "ION Orchard Live the Race (1-12 Oct 2026): Free F1 Driver Appearances, VCARB Show Car, Simulator",
                  "FISH & CHIPS + $3 SOCKS?! THAT ESCALATED QUICKLY",
                  "Museum of Ice Cream F1 Deal: Show Your Race Ticket for 35% Off Anytime Tickets",
                  "Kris+ Birthday Bash: Boosted miles, 50% off deals & more",
                  "SG Kiasu Foodies [Discounts/Promos] pinned a photo"):
            self.assertIsNone(cls(t, fnb_only=True), t)

    def test_misslobang_food_dish_headlines_still_count(self):
        # misslobang_food lost fnb_only, so these need dish words in FNB.
        for t in ("Morganfield's $14 Anniversary Specials: Baby Back Ribs, Rib Sandwich, Riblets and a Pitcher at $14 Each",
                  "Penang Culture's Big Boss Birthday: Four New Dishes at $8.80++ Each, 1-31 Oct 2026",
                  "The Soup Expert Buy 1 Get 1 Free Claypots at Suntec City: $40 Nett Spend, Till 31 Oct 2026"):
            self.assertIsNotNone(cls(t), t)

    def test_tea_museum_opening_is_not_vetoed(self):
        self.assertIsNotNone(cls("TWG Tea opens 24-hour Tea Gallery with tea museum at Changi Airport T3"))

    def test_receivership_is_not_an_opening(self):
        self.assertIsNone(cls("Crystal Jade restaurants in S'pore remain open as holding companies placed under receivership"))

    def test_just_dollar_price(self):
        c = cls("108 Matcha Saro S'pore Selling Two Soft Serves for Just $6.99 (U.P. $10) until 7 Oct 2026")
        self.assertEqual((c["kind"], c["valid_until"]), ("promo", "2026-10-07"))

    def test_price_point_promo(self):
        c = cls("KFC S'pore Most Anticipated Chicken Tuesday Returns at $10.95 on Tuesdays till 10 Nov 2026")
        self.assertEqual(c["kind"], "promo")

    def test_deal_channel_price_post(self):
        self.assertEqual(cls("$9++ BAR BITES?! AFTER-WORK PLANS = SORTED", fnb_only=True, scope="promo")["kind"], "promo")

    def test_daniel_new_outlet(self):
        c = cls("Noci Bakehouse - NEW Orchard Gateway Outlet With Exclusive Panuozzo", fnb_only=True)
        self.assertEqual(c["kind"], "opening")

    def test_first_international_foray(self):
        c = cls("OJEJE At Raffles City | Seoul's Tonkatsu & Udon Restaurant First International Foray In Singapore")
        self.assertIn("first-in-sg", c["tags"])
        self.assertEqual(c["origin"], "Korea")

    def test_and_range(self):
        c = cls("PlayMade 1-for-1 Reopening Special: 5 Drinks From $2.10 a Cup, 2 & 3 October Only")
        self.assertEqual((c["valid_from"], c["valid_until"]), ("2026-10-02", "2026-10-03"))

    def test_opening_date_is_a_start_not_an_end(self):
        c = cls("Sushiro Opens at Hougang Mall on October 5 with 1-FOR-1 Sushi Deals")
        self.assertEqual((c["valid_from"], c["valid_until"]), ("2026-10-05", None))

    def test_hawker_closures_dropped(self):
        self.assertIsNone(cls("October hawker centre closures to take note of", fnb_only=True))


class Classify(unittest.TestCase):
    def test_one_for_one_with_end_date(self):
        c = cls("McDonald's 1-for-1 McSpicy via app till 12 Oct 2026")
        self.assertEqual(c["kind"], "promo")
        self.assertEqual(c["merchants"], ["McDonald's"])
        self.assertIn("1-for-1", c["tags"])
        self.assertIn("app-only", c["tags"])
        self.assertEqual(c["valid_until"], "2026-10-12")

    def test_pct_and_same_month_range(self):
        c = cls("Starbucks: 50% off second handcrafted drink (3 - 5 Oct)")
        self.assertEqual(c["pct"], 50)
        self.assertEqual((c["valid_from"], c["valid_until"]), ("2026-10-03", "2026-10-05"))

    def test_dollar_off_is_not_a_cheap_price(self):
        # "$10 off" once read as a $1 price.
        c = cls("KFC $10 off delivery orders above $40 this weekend")
        self.assertNotIn("cheap", c["tags"])
        self.assertEqual(c["valid_until"], "2026-10-04")   # Sunday after a Saturday

    def test_cheap_price(self):
        self.assertIn("cheap", cls("Ya Kun kaya toast set at $4.90 for members from 6 Oct")["tags"])

    def test_overseas_first_outlet(self):
        c = cls("Famous Tokyo bakery opens first outlet in Singapore at ION Orchard")
        self.assertEqual(c["kind"], "opening")
        self.assertEqual(c["origin"], "Japan")
        self.assertIn("first-in-sg", c["tags"])

    def test_menu_launch_is_not_an_opening(self):
        self.assertIsNone(cls("Chagee launches new oolong series"))

    def test_non_fnb_sale_dropped(self):
        self.assertIsNone(cls("Shopee 10.10 sale: up to 90% off electronics"))

    def test_food_words_in_excerpt_alone_do_not_make_fnb(self):
        self.assertIsNone(cls("Uniqlo 20% off all jeans", "Grab a coffee after shopping"))

    def test_fnb_only_publisher_trusts_its_excerpt(self):
        c = cls("10 new openings this October", "cafes and bakeries", fnb_only=True)
        self.assertEqual(c["kind"], "opening")

    def test_gluten_free_is_not_free(self):
        c = cls("Gluten-free bakery 20% off sourdough")
        self.assertNotIn("free", c["tags"])

    def test_closure_dropped_but_closing_sale_kept(self):
        self.assertIsNone(cls("Popular hawker stall closes for good after 40 years"))
        self.assertEqual(cls("Bakery closing down sale: 50% off all bread")["kind"], "promo")

    def test_ends_today(self):
        self.assertEqual(cls("LiHO free cheese foam topping today only")["valid_until"], "2026-10-03")

    def test_card_tag_suppresses_member(self):
        c = cls("DBS cardmembers enjoy 1-for-1 buffet at Carousel till 30 Nov")
        self.assertIn("card", c["tags"])
        self.assertNotIn("member", c["tags"])
        self.assertEqual(c["category"], "buffet")

    def test_apostrophe_optional_and_accents(self):
        self.assertEqual(cls("McDonalds free fries")["merchants"], ["McDonald's"])

    def test_macs_is_not_mcdonalds(self):
        c = cls("Apple Macs 10% off, free coffee at launch")
        self.assertNotIn("McDonald's", c["merchants"])


class Validity(unittest.TestCase):
    def v(self, s):
        a, b = extract_validity(fold(s), REF)
        return (a.isoformat() if a else None, b.isoformat() if b else None)

    def test_cross_month_range(self):
        self.assertEqual(self.v("28 Sep - 5 Oct 2026"), ("2026-09-28", "2026-10-05"))

    def test_month_first(self):
        self.assertEqual(self.v("valid until October 31, 2026"), (None, "2026-10-31"))

    def test_year_rollover(self):
        # Published in Oct, "till 15 Jan" means next January.
        self.assertEqual(self.v("till 15 Jan"), (None, "2027-01-15"))

    def test_recent_past_stays_this_year(self):
        self.assertEqual(self.v("until 30 Sep"), (None, "2026-09-30"))

    def test_weekday_in_range(self):
        self.assertEqual(self.v("from 6 Oct to Sun 12 Oct"), ("2026-10-06", "2026-10-12"))

    def test_today_only_with_stated_date(self):
        # Miss Lobang cards have no publish date, so "today" alone would mean the fetch day.
        self.assertEqual(self.v("mr bean 1-for-1 today only, sunday 20 september 2026"),
                         (None, "2026-09-20"))

    def test_date_only(self):
        self.assertEqual(self.v("teachers' day treats, 4 sep 2026 only: free half dozen"),
                         ("2026-09-04", "2026-09-04"))

    def test_none(self):
        self.assertEqual(self.v("great food"), (None, None))

    def test_price_is_not_a_date(self):
        self.assertEqual(self.v("$12 set lunch"), (None, None))


def item(i, title, publisher, when, tier="deals", summary=""):
    it = {"id": "i%d" % i, "title": title, "publisher": publisher, "tier": tier, "url": "https://x/%d" % i,
          "sg_source": True, "scope": "mixed", "fnb_only": True,
          "summary": summary, "published": iso(when), "fetched": iso(when)}
    it["cls"] = classify(it, LEX, when.date())
    return it


T0 = datetime(2026, 10, 3, 9, 0, tzinfo=SGT)


class Cluster(unittest.TestCase):
    def test_same_promo_two_publishers_merge(self):
        deals = D.assign([
            item(1, "McDonald's 1-for-1 McSpicy till 12 Oct", "SingPromos", T0),
            item(2, "McDonald's: 1-for-1 McSpicy deal via app (till 12 Oct)", "Great Deals", T0),
        ], [])
        self.assertEqual(len(deals), 1)
        self.assertEqual(deals[0]["publishers"], 2)

    def test_same_chain_different_promos_split(self):
        deals = D.assign([
            item(1, "McDonald's 1-for-1 McSpicy till 12 Oct", "SingPromos", T0),
            item(2, "McDonald's free medium fries with any purchase on Friday", "SingPromos", T0),
        ], [])
        self.assertEqual(len(deals), 2)

    def test_different_periods_split(self):
        deals = D.assign([
            item(1, "Starbucks 1-for-1 Frappuccino till 5 Oct", "A", T0),
            item(2, "Starbucks 1-for-1 Frappuccino till 20 Oct", "B", T0),
        ], [])
        self.assertEqual(len(deals), 2)

    def test_same_publisher_counted_once(self):
        deals = D.assign([
            item(1, "KFC 1-for-1 Zinger till 10 Oct", "Mothership.sg", T0),
            item(2, "KFC 1-for-1 Zinger burger till 10 Oct", "mothership", T0),
        ], [])
        self.assertEqual(deals[0]["publishers"], 1)

    def test_unknown_brand_opening_merges_across_wordings(self):
        deals = D.assign([
            item(1, "Seoul tonkatsu and udon chain Gyeonggi opens first overseas outlet at Raffles City", "A", T0),
            item(2, "Seoul's famous tonkatsu spot Gyeonggi lands in Singapore", "B", T0),
        ], [])
        self.assertEqual(len(deals), 1)

    def test_unknown_brands_do_not_merge(self):
        deals = D.assign([
            item(1, "Dolpan Hwajoo Korean restaurant opens at Tanjong Pagar", "A", T0),
            item(2, "Soft Order hidden Henderson cafe opens with shio pan", "B", T0),
        ], [])
        self.assertEqual(len(deals), 2)

    def test_deterministic_ids(self):
        a = D.assign([item(1, "LiHO free topping today only", "A", T0)], [])
        b = D.assign([item(1, "LiHO free topping today only", "A", T0)], [])
        self.assertEqual(a[0]["id"], b[0]["id"])


class Score(unittest.TestCase):
    def deal(self, title, when=T0, n=1):
        items = [item(i, title, "P%d" % i, when) for i in range(n)]
        return D.assign(items, [])[0]

    def test_corroboration_raises_score(self):
        self.assertGreater(D.score(self.deal("KFC 1-for-1 Zinger", n=3), REF),
                           D.score(self.deal("KFC 1-for-1 Zinger", n=1), REF))

    def test_age_decays(self):
        old = self.deal("KFC 1-for-1 Zinger", when=datetime(2026, 9, 22, 9, tzinfo=SGT))
        self.assertLess(D.score(old, REF), D.score(self.deal("KFC 1-for-1 Zinger"), REF))

    def test_bounds(self):
        s = D.score(self.deal("McDonald's 1-for-1 free fries 50% off $1 bundle today only", n=5), REF)
        self.assertTrue(0 <= s <= 100)

    def test_expired_not_live(self):
        d = self.deal("KFC 1-for-1 Zinger till 2 Oct")
        self.assertFalse(D.is_live(d, REF))

    def test_undated_promo_lapses(self):
        d = self.deal("KFC 1-for-1 Zinger", when=datetime(2026, 9, 1, 9, tzinfo=SGT))
        self.assertFalse(D.is_live(d, REF))

    def test_standing_offer_live_while_listed(self):
        d = self.deal("Din Tai Fung 1-for-1 xiao long bao for DBS cards", when=datetime(2026, 8, 1, 9, tzinfo=SGT))
        self.assertFalse(D.is_live(d, REF))
        d["last_listed"] = iso(datetime(2026, 10, 2, 9, tzinfo=SGT))   # one missed fetch: still live
        self.assertTrue(D.is_live(d, REF))
        d["last_listed"] = iso(datetime(2026, 9, 28, 9, tzinfo=SGT))   # dropped off the page
        self.assertFalse(D.is_live(d, REF))

    def test_ends_today_tag_added_at_publish(self):
        d = self.deal("LiHO free topping today only")
        self.assertIn("ends-today", D.public(d, REF)["tags"])


class TotalOutage(unittest.TestCase):
    def test_all_sources_failed_writes_nothing(self):
        srcs = [{"name": "a", "type": "rss", "url": "https://x"}, {"name": "b", "type": "rss", "url": "https://y"}]
        with mock.patch.object(F, "load_sources", return_value=srcs), \
                mock.patch.object(F, "fetch", return_value={"ok": False, "items": [], "error": "HTTP 503"}), \
                mock.patch.object(F, "write_json") as wj, \
                mock.patch.object(F.os, "replace") as rep:
            rc = F.run()
        self.assertEqual(rc, 2)
        wj.assert_not_called()
        rep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
