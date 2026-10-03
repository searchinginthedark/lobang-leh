"""Deterministic keyword classifier. No LLM: the same headline always classifies the same way.

classify(item, lexicon, today) -> dict | None
  None means "not an F&B promo or opening" and the item is dropped from deals
  (it still lands in the items ledger, so a rule change can be replayed).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta

import yaml

CATEGORIES = ("fast-food", "coffee", "bubble-tea", "bakery-dessert", "buffet", "restaurant",
              "cafe", "bar-drinks", "hawker", "grocery", "delivery", "other")


def fold(s):
    """Lowercase, ascii-fold accents, straighten quotes, so 'Häagen-Dazs’' matches 'haagen-dazs''."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return (s.replace("’", "'").replace("‘", "'").replace("–", "-")
             .replace("—", "-").replace("％", "%").lower())


from . import birthday as BD  # noqa: E402  (after fold: birthday.py imports it from here)


def _rx(words):
    return re.compile(r"(?<![\w])(?:" + "|".join(words) + r")(?![\w])")


# ---- F&B vocabulary ---------------------------------------------------------
FNB = _rx([
    r"food", r"foods", r"drinks?", r"dining", r"dine", r"restaurants?", r"caf[e]s?", r"coffee", r"kopi",
    r"teas?", r"bubble tea", r"boba", r"milk tea", r"bakery", r"bakeries", r"bread", r"cakes?",
    r"desserts?", r"ice creams?", r"gelato", r"soft serves?", r"cheesecakes?", r"bites", r"buffets?", r"brunch", r"lunch", r"dinner", r"breakfast",
    r"high tea", r"tea time", r"menu", r"burgers?", r"hamburgs?", r"pizzas?", r"chicken", r"wings", r"sushi", r"ramen",
    r"noodles?", r"rice", r"hotpot", r"hot pot", r"bbq", r"steaks?", r"seafood", r"crabs?", r"dim sum",
    r"bak kwa", r"mooncakes?", r"durians?", r"wine", r"beers?", r"cocktails?", r"bars?", r"omakase",
    r"hawkers?", r"eatery", r"eateries", r"bistro", r"kopitiam", r"prata", r"laksa", r"nasi lemak",
    r"croissants?", r"donuts?", r"doughnuts?", r"waffles?", r"matcha", r"chocolates?", r"snacks?",
    r"meals?", r"food court", r"foodcourt", r"eats?", r"fries", r"tacos?", r"pasta", r"dumplings?",
    r"bao", r"bubble teas", r"latte", r"frappuccino", r"smoothies?", r"juice", r"yogurt", r"yoghurt",
    r"soft serve", r"pastry", r"pastries", r"tarts?", r"cookies?", r"bingsu", r"mala", r"korean bbq",
    r"izakaya", r"yakiniku", r"bento", r"kaya toast", r"toast", r"grabfood", r"foodpanda", r"deliveroo",
    r"f&b", r"fnb", r"supper", r"happy hour", r"sake", r"whisky", r"spirits",
    # Dish words seen in Miss Lobang food headlines once that source lost fnb_only (2026-10-03).
    r"dishes", r"pies?", r"soups?", r"crepes?", r"cinnamon rolls?", r"buns?", r"curry", r"biryani",
    r"claypots?", r"steamboat", r"afternoon tea", r"burritos?", r"brekkie", r"mee", r"ban mian",
    r"gomtang", r"samgyetang", r"pho", r"banh mi", r"salt bread", r"bagels?", r"wagyu", r"tingkat",
    r"pudding", r"shakes?", r"tofu", r"margaritas?", r"ribs?", r"riblets", r"sandwich(?:es)?",
    # Birthday roundup perks (2026-10-03): "Free lobster after ordering...", "Free slices of salmon sashimi".
    r"lobsters?", r"sashimi", r"gyozas?", r"pretzels?",
])

# Articles that mention food but are not a deal or an opening.
NOT_A_DEAL = _rx([
    r"recipes?", r"how to make", r"food poisoning", r"sfa", r"suspended", r"fined", r"hygiene",
    r"recall(?:ed|s)?", r"cockroach(?:es)?", r"rats?", r"lawsuit", r"sued", r"job(?:s)? (?:opening|vacanc)",
    r"hiring", r"shares? (?:rose|fell|jump|drop)", r"ipo", r"quarterly results", r"profit",
    r"closing down", r"closes? (?:its|for good|permanently|all)", r"shutters?", r"ceases?",
    r"receivership", r"liquidation", r"bankrupt(?:cy)?", r"remains? open", r"cost of opening", r"closures?",
])

# A non-food product or event in the headline vetoes the item outright, food words or not:
# "FISH & CHIPS + $3 SOCKS" is a socks deal, "Museum of Ice Cream ... 35% Off Anytime Tickets"
# is a ticket deal. Every entry here was a live misfire (2026-10-03), so keep it to things that
# are never F&B; "toys" stays out because a Happy Meal toy is still a meal deal.
NON_FNB = _rx([
    r"bed ?sheets?", r"bedding", r"mattress(?:es)?", r"duvets?", r"pillows?", r"lego", r"astro bot",
    r"f1 drivers?", r"driver appearances?", r"show car", r"sim racing", r"superpark", r"trampoline",
    r"(?:anytime|entry|admission|race|concert|movie|event) tickets?", r"socks", r"keychains?",
    r"(?:boosted|bonus|earn|kris\+?) miles", r"\d+ ?mpd", r"staycations?", r"skincare", r"cosmetics",
    r"pinned an? (?:photo|message|file|video|poll)",
])

# ---- Singapore relevance ----------------------------------------------------
# Every RSS/Telegram source is an SG publisher; Google News is global, so a gnews item
# needs an SG publisher or an SG word in its headline. Measured 2026-10-03: without this,
# Toronto, Seattle and US Chick-fil-A openings made up a third of gnews "openings".
SG_WORDS = _rx([r"singapore", r"s'pore", r"spore", r"sg", r"singaporeans?", r"orchard", r"jewel", r"vivocity",
                r"bugis", r"tampines", r"jurong", r"punggol", r"sengkang", r"marina bay", r"mbs", r"raffles city",
                r"funan", r"suntec", r"plaza singapura", r"paya lebar", r"changi", r"tanjong pagar", r"chinatown",
                r"katong", r"tiong bahru", r"clementi", r"woodlands", r"yishun", r"bishan", r"toa payoh", r"hougang"])
SG_PUBLISHER = re.compile(r"singapore|s'pore|\bsg\b|eatbook|seth ?lui|mothership|straits ?times|channel ?news ?asia|"
                          r"\bcna\b|today ?online|great ?deals|singpromos|miss ?lobang|confirm ?good|smart ?local|"
                          r"honeycombers|lady ?iron ?chef|daniel ?food|miss ?tam ?chiak|8 ?days|asiaone|lifestyle ?news|"
                          r"burpple|goody ?feed|must ?share|vulcan ?post|little ?big ?red ?dot|stomp|ranting ?panda|"
                          r"zaobao|the ?new ?paper|sgmag|hungrygowhere|kiasu")
# Not "Time Out" (Time Out Worldwide covers London) and not Yahoo News Singapore, which
# syndicates US wire copy ("Dunkin', L.L. Bean launch merch collab"): both need an SG headline.
UNTRUSTED_PUBLISHER = re.compile(r"yahoo|msn|time ?out worldwide")
_FOREIGN = (r"jb|johor(?: bahru)?|malaysia|kuala lumpur|kl|penang|ipoh|melaka|batam|bintan|bangkok|hong kong|hk|"
            r"taipei|tokyo|osaka|seoul|shanghai|beijing|sydney|melbourne|london|new york|nyc|toronto|seattle|"
            r"orlando|los angeles|dubai|bali|jakarta|manila|vancouver|chicago|texas|california")
FOREIGN_PLACE = re.compile(r"(?<![\w])(?:in|to|at|around|across|over|all over)\s+(?:the\s+)?(?:" + _FOREIGN + r")(?![\w])"
                           r"|(?<![\w])(?:jb|johor|malaysia|kl)\s+(?:cafes?|food|restaurants?|eats?|hawkers?|openings?)(?![\w])")
# ...except a closing-down sale is a genuine lobang; strong promo signals override NOT_A_DEAL.

# ---- promo signals ----------------------------------------------------------
ONE_FOR_ONE = re.compile(r"(?<![\w$.])(?:1|one)\s*-?\s*for\s*-?\s*(?:1|one)(?![\w])|\bbuy\s*(?:1|one)\s*(?:get|free)\s*(?:1|one)\b|\bb1g1\b|\bbogo\b")
PCT_OFF = re.compile(r"(?<![\d.])(\d{1,2})\s*(?:%|per\s?cent)\s*(?:off|discount)")
UP_TO_PCT = re.compile(r"up to\s*(\d{1,2})\s*(?:%|per\s?cent)")
FREE = re.compile(r"(?<![\w-])free(?![\w-])(?!\s*(?:-|\s)?flow)")
NOT_FREE = re.compile(r"(?:gluten|sugar|dairy|alcohol|cruelty|nut|meat|egg|guilt|hassle|stress|msg|caffeine|lactose|smoke|cash|duty|tax|scam|car)[\s-]free")
PRICE = re.compile(r"(?:s\$|\$)\s?(\d{1,3}(?:\.\d{1,2})?)(?![\d.])(?!\s*(?:off|cashback|rebate|voucher|credit|million|mil|k\b|bn|billion))")
DOLLAR_OFF = re.compile(r"(?:s\$|\$)\s?\d{1,3}(?:\.\d{1,2})?\s*(?:off|cashback|rebate|voucher)")
PROMO_WORDS = _rx([
    r"promos?", r"promotions?", r"deals?", r"discounts?", r"vouchers?", r"coupons?", r"offers?",
    r"sale", r"lobangs?", r"happy hour", r"cashback", r"rebates?", r"for only", r"at only",
    # A price after a preposition is a price point ("returns at $10.95", "2 slices for $10").
    # Must end on a digit: _rx's trailing (?![\w]) would reject a bare "\$" before the number.
    r"(?:at|for|from|only|just|now)\s+s?\$\d+", r"u\.p\.", r"usual(?:ly)? (?:price|\$\d+)", r"one[- ]day",
    r"flash sale", r"redeem", r"freebies?", r"giveaways?", r"specials?", r"limited[- ]time",
    r"members?[- ]only", r"value meal", r"\d+\.\d+ sale", r"price drop", r"cheapest", r"budget",
    r"under \$\d+", r"below \$\d+", r"from \$\d+",
])
BUNDLE = _rx([r"bundles?", r"combos?", r"sets? for (?:2|two|4|four)", r"meal for (?:2|two)", r"family (?:feast|bundle|meal)", r"platter"])
APP_ONLY = _rx([r"via (?:the )?app", r"in-app", r"app[- ](?:exclusive|only|users?)", r"on the app", r"through the app", r"e-?coupons?"])
CARD = _rx([r"cardmembers?", r"cardholders?", r"credit card", r"debit card", r"dbs", r"posb", r"uob", r"ocbc",
            r"citi(?:bank)?", r"amex", r"american express", r"hsbc", r"maybank", r"standard chartered", r"trust bank",
            r"paylah", r"visa", r"mastercard"])
MEMBER = _rx([r"members?", r"membership", r"rewards?", r"loyalty", r"subscribers?", r"app members?"])
DELIVERY = _rx([r"grabfood", r"foodpanda", r"deliveroo", r"delivery", r"islandwide delivery"])
LIMITED = _rx([r"limited[- ]time", r"while stocks? last", r"first \d+ customers?", r"limited edition",
               r"one[- ]day only", r"today only", r"this weekend only", r"limited (?:quantities|stocks?)", r"flash sale"])
ENDS_TODAY = _rx([r"ends? today", r"today only", r"last day", r"one[- ]day only"])

# ---- opening signals --------------------------------------------------------
OPENING = _rx([
    # Not bare "launches"/"debuts"/"arrives": "McDonald's launches Samurai burger" is a menu item, not an
    # outlet. Those verbs only count with "in Singapore", which FIRST_IN_SG covers.
    r"opens?", r"opening", r"opened",r"coming to singapore", r"comes to singapore", r"now in singapore",
    r"soft launch", r"grand opening", r"new outlets?", r"new stores?", r"new branch(?:es)?", r"new locations?",
    r"first outlet", r"first store", r"flagship", r"expands? to singapore", r"heads? to singapore",
    r"\[new\]",
    # "Noci Bakehouse - NEW Orchard Gateway Outlet", "New Hokkaido-Style Soup Curry Eatery"
    r"new (?:[\w&'-]+[ -]){0,4}?(?:restaurants?|caf[e]s?|eater(?:y|ies)|openings?|spots?|bakery|bakeries|bars?|"
    r"outlets?|stalls?|kiosks?|shops?|stores?|branch(?:es)?|concepts?|buffets?|hawker|bakehouse|izakaya)",
])
FIRST_IN_SG = re.compile(
    r"first[- ](?:ever[- ])?(?:\w+[- ]){0,2}(?:outlet|store|shop|branch|restaurant|location|cafe|kiosk)s?\s+(?:in|outside of|outside)\s+(?:singapore|sg|southeast asia|sea|asia)"
    r"|first (?:singapore|sg) (?:outlet|store|shop|branch|restaurant|location)"
    r"|first (?:international|overseas) (?:foray|outlet|store|branch|expansion|location)"
    # "makes its Singapore debut", not "Starbucks Singapore Debuts Protein Cold Foam" (a menu item).
    r"|(?:singapore|sg) debut(?!s)|(?:debuts?|launch(?:es|ed)?|opens?|opened) in (?:singapore|sg)|(?:arrives?|lands?|comes?|coming|heads?|expands?) (?:in|to) (?:singapore|sg)"
    r"|now (?:open )?in (?:singapore|sg)|makes? (?:its|their) way to (?:singapore|sg)|first (?:time )?in (?:singapore|sg)"
)

COUNTRIES = {
    "Japan": ["japan", "japanese", "tokyo", "osaka", "kyoto", "hokkaido", "fukuoka", "nagoya", "okinawa", "sapporo"],
    "Korea": ["korea", "korean", "seoul", "busan"],
    "Taiwan": ["taiwan", "taiwanese", "taipei", "tainan", "taichung"],
    "China": ["china", "chinese brand", "shanghai", "beijing", "chengdu", "shenzhen", "guangzhou", "chongqing", "changsha"],
    "Hong Kong": ["hong kong", "hk-based"],
    "Thailand": ["thailand", "thai", "bangkok", "chiang mai"],
    "Malaysia": ["malaysia", "malaysian", "kuala lumpur", "penang", "johor", "ipoh"],
    "Indonesia": ["indonesia", "indonesian", "jakarta", "bali"],
    "Vietnam": ["vietnam", "vietnamese", "hanoi", "ho chi minh", "saigon"],
    "Philippines": ["philippines", "filipino", "manila"],
    "USA": ["american", "new york", "nyc", "los angeles", "california", "us-based", "us chain", "san francisco", "hawaii", "texas"],
    "UK": ["british", "london", "uk-based", "uk chain"],
    "Australia": ["australia", "australian", "melbourne", "sydney", "brisbane", "perth"],
    "France": ["french", "paris", "parisian"],
    "Italy": ["italian brand", "milan", "rome", "naples"],
    "Spain": ["spanish brand", "barcelona", "madrid"],
}
# A country word only means "overseas brand" next to a brand-ish noun or "from/famous/viral";
# "Japanese restaurant" alone is a cuisine, not an import.
ORIGIN_CTX = re.compile(r"(?:from|famous|popular|viral|iconic|beloved|cult|hit|hyped|renowned|chain|brand|import)")

CATEGORY_WORDS = [
    ("bubble-tea", ["bubble tea", "bubble teas", "boba", "milk tea", "fruit tea", "brown sugar"]),
    ("coffee", ["coffee", "kopi", "latte", "espresso", "frappuccino", "americano"]),
    ("buffet", ["buffet", "buffets"]),
    ("bakery-dessert", ["cake", "cakes", "dessert", "desserts", "ice cream", "gelato", "bakery", "bread", "pastry",
                        "pastries", "croissant", "croissants", "donut", "donuts", "doughnut", "doughnuts", "waffle",
                        "soft serve", "bingsu", "tart", "tarts", "cookie", "cookies", "mooncake", "mooncakes", "chocolate"]),
    # After desserts, so "chocolate bar" is a dessert.
    ("bar-drinks", ["happy hour", "beer", "beers", "wine", "cocktail", "cocktails", "bar", "bars", "whisky", "sake", "spirits", "izakaya"]),
    ("hawker", ["hawker", "kopitiam", "food court", "foodcourt", "prata", "laksa", "nasi lemak", "char kway teow", "chicken rice"]),
    ("fast-food", ["burger", "burgers", "fried chicken", "pizza", "pizzas", "fries", "nuggets"]),
    ("delivery", ["grabfood", "foodpanda", "deliveroo"]),
    ("grocery", ["supermarket", "grocery", "groceries"]),
    ("cafe", ["cafe", "cafes", "brunch"]),
    ("restaurant", ["restaurant", "restaurants", "dining", "omakase", "ramen", "sushi", "hotpot", "hot pot", "steak",
                    "dim sum", "yakiniku", "korean bbq", "seafood", "bistro", "eatery", "mala"]),
]
_CAT_RX = [(c, _rx([re.escape(w) for w in ws])) for c, ws in CATEGORY_WORDS]

# ---- validity dates ---------------------------------------------------------
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_MON = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_DAY = r"(\d{1,2})(?:st|nd|rd|th)?"
_YR = r"(?:,?\s*(20\d\d))?"
_WD = r"(?:(?:mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)(?:day|nesday|sday|urday|rsday)?,?\s+)?"
# "3 Oct" / "3rd October 2026" / "Oct 3" / "October 3, 2026"
DATE_DM = _DAY + r"\s+" + _MON + r"\.?" + _YR
DATE_MD = _MON + r"\.?\s+" + _DAY + _YR
# "3 - 12 Oct 2026", "3 to 12 October", "1-31 Oct"
RANGE_SAME_MONTH = re.compile(r"(?<!\d)" + _DAY + r"\s*(?:-|to|till|until|&|and)\s*" + _WD + _DAY + r"\s+" + _MON + r"\.?" + _YR)
# "28 Sep - 5 Oct 2026", "Sep 28 to Oct 5"
RANGE_DM = re.compile(r"(?<!\d)" + DATE_DM + r"\s*(?:-|to|till|until)\s*" + _WD + DATE_DM)
RANGE_MD = re.compile(DATE_MD + r"\s*(?:-|to|till|until)\s*" + _WD + DATE_MD)
UNTIL = re.compile(r"(?:till|until|til|thru|through|ends?|ending|valid (?:till|until|through)|by|before|up to)\s+" + _WD + r"(?:" + DATE_DM + r"|" + DATE_MD + r")")
FROM = re.compile(r"(?:from|starting|starts?|begins?|available from)\s+" + _WD + r"(?:" + DATE_DM + r"|" + DATE_MD + r")")
ON_DAY = re.compile(r"(?:\bon\s+" + _WD + r"|\(\s*" + _WD + r")(?:" + DATE_DM + r"|" + DATE_MD + r")\s*\)?")
# "Teachers' Day Treats, 4 Sep 2026 Only" is a one-day deal on that date.
DAY_ONLY = re.compile(r"(?<!\d)(?:" + DATE_DM + r"|" + DATE_MD + r")\s*only\b")
ANY_DATE = re.compile(r"(?<!\d)(?:" + DATE_DM + r"|" + DATE_MD + r")")
THIS_WEEKEND = _rx([r"this weekend", r"this sat(?:urday)?(?: and|\s*&)\s*sun(?:day)?"])


def _mkdate(day, mon, year, ref):
    """A date with no year is placed so it falls in [ref - 60 days, ref + 300 days]."""
    try:
        d = int(day)
        m = MONTHS[mon[:3]]
        if year:
            return date(int(year), m, d)
        cand = date(ref.year, m, d)
        if cand < ref - timedelta(days=60):
            cand = date(ref.year + 1, m, d)
        return cand
    except (ValueError, KeyError):
        return None


def _dm_or_md(groups, ref, md=False):
    # groups for one DATE_DM: (day, mon, year); for DATE_MD: (mon, day, year)
    if md:
        return _mkdate(groups[1], groups[0], groups[2], ref)
    return _mkdate(groups[0], groups[1], groups[2], ref)


def _alt_date(g, ref):
    """Groups from (DATE_DM|DATE_MD) alternation: 6 groups, one side is None."""
    if g[0] is not None:
        return _mkdate(g[0], g[1], g[2], ref)
    if g[3] is not None:
        return _mkdate(g[4], g[3], g[5], ref)
    return None


def extract_validity(text, ref):
    """(valid_from, valid_until) as date|None from folded text; ref = the item's SG publish date."""
    t = text
    m = RANGE_DM.search(t)
    if m:
        g = m.groups()
        end = _mkdate(g[3], g[4], g[5], ref)
        start = _mkdate(g[0], g[1], g[2] or (g[5] if end else None), ref)
        if start and end and start > end and not g[2]:
            start = start.replace(year=start.year - 1)
        if end:
            return start, end
    m = RANGE_MD.search(t)
    if m:
        g = m.groups()
        end = _mkdate(g[4], g[3], g[5], ref)
        start = _mkdate(g[1], g[0], g[2] or (g[5] if end else None), ref)
        if start and end and start > end and not g[2]:
            start = start.replace(year=start.year - 1)
        if end:
            return start, end
    m = RANGE_SAME_MONTH.search(t)
    if m:
        d1, d2, mon, yr = m.groups()
        end = _mkdate(d2, mon, yr, ref)
        start = _mkdate(d1, mon, yr or (str(end.year) if end else None), ref)
        if start and end and start <= end:
            return start, end
    start = end = None
    m = UNTIL.search(t)
    if m:
        end = _alt_date(m.groups(), ref)
    m = FROM.search(t)
    if m:
        start = _alt_date(m.groups(), ref)
    if end:
        return start, end
    m = ON_DAY.search(t)
    if m:
        d = _alt_date(m.groups(), ref)
        if d and d >= ref - timedelta(days=1):
            # "Mixue $1 ice cream on 10 Oct" is a one-day deal; "Sushiro opens on 1 Oct with
            # 1-for-1" is a start date, and its promo runs past it.
            return (d, None) if OPENING.search(t) else (d, d)
    m = DAY_ONLY.search(t)
    if m:
        d = _alt_date(m.groups(), ref)
        if d:
            return d, d
    if ENDS_TODAY.search(t):
        # "Today Only, Sunday 20 September 2026": the stated date wins over the publish
        # date, which for an undated scraped card is only the day we first saw it.
        m = ANY_DATE.search(t)
        d = _alt_date(m.groups(), ref) if m else None
        return start, d or ref
    if THIS_WEEKEND.search(t):
        sunday = ref + timedelta(days=(6 - ref.weekday()) % 7)
        return start, sunday
    return start, None


# ---- merchants --------------------------------------------------------------
class Lexicon(object):
    def __init__(self, merchants):
        self.by_name = {}
        pats = []
        for m in merchants:
            self.by_name[m["name"]] = m
            for alias in [m["name"]] + list(m.get("aliases") or []):
                a = fold(alias).strip()
                if len(a) < 2:
                    continue
                # Apostrophes are optional: "McDonalds" and "McDonald's" are both common.
                body = re.escape(a).replace("'", "'?")
                pats.append((len(a), body, m["name"]))
        pats.sort(key=lambda p: -p[0])  # longest first, so "Coffee Bean & Tea Leaf" beats "Coffee Bean"
        self._names = [p[2] for p in pats]
        self._rx = re.compile("|".join("(?<![\\w])({0})(?![\\w])".format(p[1]) for p in pats)) if pats else None

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return cls(data.get("merchants") or [])

    def find(self, folded):
        if not self._rx:
            return []
        out = []
        for m in self._rx.finditer(folded):
            idx = m.lastindex - 1
            name = self._names[idx]
            if name not in out:
                out.append(name)
        return out[:3]


# ---- the classifier -----------------------------------------------------------
def classify(item, lex, ref):
    """ref: the item's SG publish date (or today). Returns the deal attributes or None."""
    title = fold(item["title"])
    text = title + " \n " + fold(item.get("summary") or "")
    summary = fold(item.get("summary") or "")
    pub = fold(item.get("publisher") or "")
    sg = (item.get("sg_source")
          or (bool(SG_PUBLISHER.search(pub)) and not UNTRUSTED_PUBLISHER.search(pub))
          or bool(SG_WORDS.search(title)))
    if not sg or (FOREIGN_PLACE.search(title) and not SG_WORDS.search(title)):
        return None
    if NON_FNB.search(title):
        return None
    # Merchants come from the HEADLINE only: an excerpt names merchants as landmarks
    # ("a Japanese chain opens near Lau Pa Sat"), which mislabelled openings.
    merchants = lex.find(title)
    summary_merchants = lex.find(summary)
    # Deal aggregators post every kind of promo, so F&B evidence must be in the headline
    # (or a known merchant plus food words in the excerpt). Food-only publishers skip this.
    fnb = (item.get("fnb_only") or bool(merchants) or bool(FNB.search(title))
           or (bool(summary_merchants) and bool(FNB.search(summary))))
    if not fnb:
        return None

    tags = []
    pct = None
    one4one = bool(ONE_FOR_ONE.search(text))
    if one4one:
        tags.append("1-for-1")
    pm = PCT_OFF.search(text) or UP_TO_PCT.search(text)
    if pm and 5 <= int(pm.group(1)) <= 95:
        pct = int(pm.group(1))
        tags.append("pct-off")
    free = bool(FREE.search(text)) and not NOT_FREE.search(text)
    if free:
        tags.append("free")
    # Headline only: excerpts quote menu prices ("cold foam add-on $1") that are not deals.
    prices = [float(p) for p in PRICE.findall(title) if 0 < float(p) <= 5]
    if prices:
        tags.append("cheap")
    strong = one4one or pct is not None or free or bool(prices) or bool(DOLLAR_OFF.search(text))
    # A deal channel posting a price IS posting a deal ("$9++ bar bites?!").
    weak = bool(PROMO_WORDS.search(text)) or (item.get("scope") == "promo" and bool(re.search(r"s?\$\d", title)))

    opening = bool(OPENING.search(title)) or bool(FIRST_IN_SG.search(text))
    first_sg = bool(FIRST_IN_SG.search(text))
    bday = BD.is_customer(item["title"], item.get("summary") or "", item.get("birthday_only"))

    if NOT_A_DEAL.search(title) and not strong:
        return None
    if bday:
        # A customer birthday perk is a promo by definition, even when it is only "a $100 voucher".
        kind, opening, first_sg = "promo", False, False
        tags.append("birthday")
    elif strong:
        kind = "promo"
    elif opening:
        kind = "opening"
    elif weak:
        kind = "promo"
    else:
        return None

    for rx, tag in ((BUNDLE, "bundle"), (APP_ONLY, "app-only"), (CARD, "card"), (DELIVERY, "delivery"),
                    (LIMITED, "limited")):
        if rx.search(text):
            tags.append(tag)
    if MEMBER.search(text) and "card" not in tags:
        tags.append("member")
    if _rx(["buffets?"]).search(text):
        tags.append("buffet")

    origin = None
    for name in merchants:
        o = lex.by_name[name].get("origin")
        if o and o.lower() not in ("singapore", "sg"):
            origin = o
            break
    if origin is None and (opening or first_sg):
        for country, words in COUNTRIES.items():
            for w in words:
                # Headline only: an excerpt of a roundup names countries for its other entries.
                for wm in re.finditer(r"(?<![\w])" + re.escape(w) + r"(?![\w])", title):
                    window = title[max(0, wm.start() - 40): wm.end() + 40]
                    if ORIGIN_CTX.search(window) or first_sg:
                        origin = country
                        break
                if origin:
                    break
            if origin:
                break
    if first_sg:
        tags.append("first-in-sg")
    if origin and (kind == "opening" or first_sg):
        tags.append("overseas")

    category = None
    for name in merchants:
        c = lex.by_name[name].get("category")
        if c in CATEGORIES:
            category = c
            break
    if category is None:
        for c, rx in _CAT_RX:
            if rx.search(title):
                category = c
                break
    if category is None:
        for c, rx in _CAT_RX:
            if rx.search(text):
                category = c
                break
    if "buffet" in tags and category in (None, "restaurant", "other"):
        category = "buffet"

    # A birthday roundup's prose carries blackout dates ("except 21st-31st December") that are
    # not an end date, so a birthday perk takes its validity from the headline only.
    vfrom, vuntil = extract_validity(title if bday else text, ref)
    famous = any(lex.by_name[n].get("famous") for n in merchants)
    out = {
        "kind": kind,
        "merchants": merchants,
        "category": category or "other",
        "tags": tags,
        "pct": pct,
        "origin": origin,
        "valid_from": vfrom.isoformat() if vfrom else None,
        "valid_until": vuntil.isoformat() if vuntil else None,
        "famous": famous,
    }
    if bday:
        b = BD.extract(item["title"], item.get("summary") or "", item.get("redeem"))
        out["birthday"] = b
        # The generic MEMBER tag fires on "you don't even need a membership" (Haidilao); the
        # birthday extractor reads the negation, so it decides.
        if "member" in tags and "member" not in b["needs"]:
            tags.remove("member")
    return out
