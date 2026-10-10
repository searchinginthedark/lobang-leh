"""Place tags (config/places.yml): every case here is a real stored headline or excerpt from the
2026-10-11 audit of 447 F&B items, or the near-miss beside it."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lobang.classify import Lexicon, fold  # noqa: E402
from lobang.places import REGIONS, merge  # noqa: E402

LEX = Lexicon.load(os.path.join(ROOT, "config", "merchants.yml"))
P = LEX.places


def names(title, summary=""):
    return [p["name"] for p in P.locate(fold(title), fold(summary))]


class Lexicon_(unittest.TestCase):
    def test_every_place_resolves_to_a_region(self):
        for e in P._entries:
            self.assertIn(e["region"], REGIONS, e["name"])

    def test_loaded_with_the_merchant_lexicon(self):
        self.assertIsNotNone(P)


class Headline(unittest.TestCase):
    def test_mall_gives_its_station_and_region(self):
        self.assertEqual(P.locate(fold("Sushiro Opens at Hougang Mall on October 1 with 1-FOR-1 Sushi"), ""),
                         [{"name": "Hougang Mall", "mrt": "Hougang", "region": "North-East"}])

    def test_longest_name_wins(self):
        self.assertEqual(names("Viral Molly Tea To Open At Hillion Mall On 9 Oct"), ["Hillion Mall"])
        self.assertEqual(names("Jurong Point 1-for-1 bubble tea"), ["Jurong Point"])

    def test_two_outlets_in_order(self):
        self.assertEqual(names("PlayMade 1-for-1 reopening deal at Westgate & Waterway Point on 2-3 Oct"),
                         ["Westgate", "Waterway Point"])

    def test_neighbourhood_without_a_station(self):
        self.assertEqual(P.locate(fold("Elijah Pies Opens Its Joo Chiat Flagship"), ""),
                         [{"name": "Joo Chiat", "mrt": None, "region": "East"}])

    def test_mall_and_its_own_station_are_one_place(self):
        self.assertEqual(names("New cafe at VivoCity, near HarbourFront MRT"), ["VivoCity"])

    def test_qualified_station_needs_mrt(self):
        self.assertEqual(names("Lavender latte 1-for-1 at Starbucks"), [])
        self.assertEqual(names("New prata shop near Lavender MRT"), ["Lavender"])
        self.assertEqual(names("Expo-themed buffet for $25"), [])

    def test_ion_water_is_not_ion_orchard(self):
        self.assertEqual(names("7-Eleven $1 Deals: From Lotus Biscoff and Pocari Sweat Ion Water to Twisties"), [])

    def test_brand_named_after_a_place_is_ignored(self):
        self.assertEqual(names("Tiong Bahru Bakery 1-for-1 croissants"), [])
        self.assertEqual(names("Tiong Bahru Bakery opens at Funan"), ["Funan"])

    def test_chain_wide_deal_has_no_place(self):
        self.assertEqual(names("4Fingers Day: 4 Wingettes for S$4 at all outlets except Changi Airport"), [])


class Excerpt(unittest.TestCase):
    def test_short_deal_channel_excerpt_counts(self):
        self.assertEqual(names("Molly Tea: 1-for-1 selected drinks", "9-11 Oct Hillion Mall T&Cs apply, more info here"),
                         ["Hillion Mall"])

    def test_headline_beats_excerpt(self):
        self.assertEqual(names("Beard Papa's Bugis Junction Opens", "Also at Tampines Mall"), ["Bugis Junction"])

    def test_excluded_outlets_are_not_where(self):
        self.assertEqual(names("$9++ BAR BITES?!", "LOCATION: Harry's outlets islandwide, excluding Changi Airport T1, T2 & T3"), [])
        self.assertEqual(names("4Fingers Day", "for dine-in and takeaway at all outlets except Changi Airport."), [])

    def test_long_prose_without_a_unit_number_is_not_trusted(self):
        prose = ("Starbucks Singapore is selling any two Tall drinks for $9.90 from Monday 5 to Thursday 8 October "
                 "2026, which works out to $4.95 a cup. Redemption is in store only, between 2pm and 8pm, and "
                 "Reserve drinks and the exclusive drinks at Starbucks WEAVE in Resorts World Sentosa are out.")
        self.assertEqual(names("Starbucks Rewards: Any 2 Tall Drinks for $9.90", prose), [])

    def test_long_excerpt_with_a_unit_number_counts(self):
        s = ("Enjoy exciting 1-for-1 opening deals on the signature Custard Pie Cream Puff, our best seller, "
             "with a dozen flavours to choose from and a free gift for the first fifty customers every day. "
             "Now till 30 Sep, Bugis Junction, #B1-K05 Find out more")
        self.assertGreater(len(s), 240)
        self.assertEqual(names("Beard Papa's: 1-for-1 Opening Promo", s), ["Bugis Junction"])

    def test_outlet_list_is_not_where(self):
        s = "Available at Jurong Point, Parkway Parade and Changi Airport T3."
        self.assertEqual(names("Cheese Tart Buy 1 Free 1", s), [])


class Merge(unittest.TestCase):
    def test_mall_and_station_from_two_posts_merge(self):
        gwc = {"name": "Great World City", "mrt": "Great World", "region": "Central"}
        gw = {"name": "Great World", "mrt": "Great World", "region": "Central"}
        self.assertEqual(merge([gwc, gw, gwc]), [gwc])

    def test_capped_at_three(self):
        ps = [{"name": n, "mrt": None, "region": "East"} for n in "ABCD"]
        self.assertEqual(len(merge(ps)), 3)


if __name__ == "__main__":
    unittest.main()
