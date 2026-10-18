"""Structured attributes of a deal, read from its own words, and the ease score built on them.

    extract(title, text, tags, birthday=None) -> {"cost", "price", "needs", "min_spend", "checked", "ease"}

`needs` is what a reader must do or be to get the deal, from a fixed vocabulary (NEEDS, in
display order). `ease` is 100 minus the cost of those needs: the Hot order rewards a deal you can
walk in and claim over one behind a bank card, an app sign-up or a lucky draw. Nothing here is
guessed: a need is listed only when the post states it, and `checked` says whether there was
enough text to look (a headline alone rarely states its conditions, so "no needs" there means
UNKNOWN, never "no catch").
"""

from __future__ import annotations

import re

from .classify import CARD, FREE, NOT_FREE, ONE_FOR_ONE, PCT_OFF, PRICE, fold

# need -> ease points it costs. A lucky draw is not a deal you can count on; a specific bank card
# or an eligibility rule shuts most readers out; an app or a code is one minute of friction.
COST = {
    "contest": 45, "eligible": 25, "card": 18, "min-spend": 12, "member": 12, "social": 10,
    "purchase": 10, "group": 8, "booking": 8, "first-n": 8, "app": 8, "delivery": 4,
    "one-day": 4, "hours": 4, "days": 3, "code": 3,
}
NEEDS = ("contest", "eligible", "card", "member", "app", "min-spend", "purchase", "group",
         "booking", "first-n", "social", "delivery", "code", "one-day", "days", "hours")
CHECK_MIN = 80        # chars of the post's own text needed before an empty `needs` means anything
TEXT_MAX = 1500       # only the opening of a long post: a listicle's later entries have their own rules


def _rx(*pats):
    return re.compile(r"(?<![\w])(?:" + "|".join(pats) + r")(?![\w])")


# "No minimum spend required", "you don't even need a membership": stated absences, cut from the
# text before any need is looked for, so they can never fire it.
NEGATED = re.compile(
    r"(?:no|without(?: any)?|not|don'?t (?:even )?need(?: a| an| to)?|doesn'?t require|no need (?:for|to)(?: a| an)?)\s+"
    r"(?:a |an |any )?(?:min(?:imum|\.)? ?(?:spend|purchase|order)|purchase|membership|members?|sign[- ]?ups?|"
    r"registration|app|code|promo code|booking|reservations?|catch|strings attached)"
    r"(?: (?:is |are )?(?:required|needed|necessary))?"
    # "cannot be combined with credit card or membership deals" names other offers, not a need.
    r"|(?:cannot|can't|can ?not|not to) be (?:combined|used|stacked) (?:together )?with[^.;\n]{0,80}"
    r"|not valid (?:with|in conjunction with)[^.;\n]{0,80}")

CONTEST = _rx(r"giveaways?", r"stand a chance", r"lucky draws?", r"contests?", r"to win", r"win (?:a|an|one|free)",
              r"winners? will", r"be one of (?:the )?\d+ (?:lucky )?winners")
ELIGIBLE = _rx(r"students? only", r"for students", r"student (?:meals?|deals?|discounts?|prices?|card|id|pass)",
               r"with (?:a |your )?student", r"seniors? only", r"for seniors", r"senior citizens?", r"nsmen", r"nsf",
               r"healthcare workers?", r"ladies'? nights?", r"for ladies", r"pioneer generation", r"merdeka generation",
               r"saf (?:personnel|servicemen)", r"teachers? only", r"for teachers", r"children only", r"kids eat free")
# The headline can say it plainly ("for Members", "New users extra 30% off"); the body must say it as
# a requirement, because posts also mention membership as a side tip ("free app membership pays for
# itself") next to a deal that needs none.
CARD_HEAD = _rx(r"bank cards?", r"cards? (?:holders?|members?)")
CARD_STRICT = _rx(r"cardholders?", r"cardmembers?", r"card members?", r"cards from (?:ocbc|dbs|posb|uob|citi|hsbc|maybank|amex|trust)",
                  r"(?:with|using|via) (?:\d+|selected|participating) bank cards?",
                  r"with (?:your |a |selected |participating )?"
                  r"(?:[a-z/]+ ){0,3}(?:credit|debit|bank) cards?", r"(?:credit|debit|bank) cards? (?:only|exclusive)",
                  r"(?:dbs|posb|uob|ocbc|citi(?:bank)?|hsbc|maybank|amex|standard chartered|trust)(?:/[a-z]+)? cards? (?:only|exclusive)",
                  r"(?:pay|paying|payment) (?:with|via|using) (?:your |a )?(?:dbs|posb|uob|ocbc|citi(?:bank)?|hsbc|maybank|amex|trust)")
MEMBER_HEAD = _rx(r"members?", r"membership", r"new users?", r"subscribers?", r"loyalty")
MEMBER = _rx(r"members? only", r"members?[- ]exclusive", r"(?:exclusively |only )?for (?:all )?(?:new |existing )?members",
             r"sign[- ]?up (?:as|for|with|to|via)", r"register (?:as|for|with|via|through)", r"registration (?:is )?required",
             r"join (?:as|the) [a-z' ]{0,30}(?:member|club|programme|program|rewards)", r"must be a member",
             r"(?:need|have) to (?:be a member|sign up|register)", r"members? (?:enjoy|get|can|will)")
# Up to three words of app name: "via the LiHo TEA app", "download the Boost Juice Singapore app".
APP = _rx(r"(?:via|on|in|through|using|with) (?:the |our |their )?(?:[a-z0-9'&.-]+ ){0,3}app", r"in-app", r"app[- ]only",
          r"app[- ]exclusive", r"download (?:the |our )?(?:[a-z0-9'&.-]+ ){0,3}app", r"app users?", r"e-?coupons?",
          r"app (?:rewards?|deals?|vouchers?|coupons?)")
APP_OPTIONAL = re.compile(r"app,? or (?:\w+ ){0,3}in[- ]?store|in[- ]?store or (?:\w+ ){0,3}app|app or walk[- ]in")
MIN_SPEND = re.compile(r"(?<![\w])(?:min(?:imum|\.)?\s*(?:spend|purchase|order|of)|spend(?:ing)? (?:at least|over|above|a minimum of)?)"
                       r"\s*(?:of\s*)?(?:s\$|\$)\s?(\d{1,4}(?:\.\d{1,2})?)")
MIN_SPEND_BARE = _rx(r"min(?:imum|\.)? ?spend", r"minimum (?:purchase|order)")
PURCHASE = _rx(r"with (?:any|every|each|a|the|min(?:imum)?) (?:\w+ )?(?:purchase|order)", r"with purchase",
               r"with (?:any|every|each|a|the) (?:[\w'-]+ ){1,5}(?:meals?|drinks?|mains?|sets?|bowls?|buckets?|burgers?|pizzas?)",
               r"when you (?:buy|order|purchase|spend)", r"upon (?:purchase|ordering)", r"purchase of (?:any|a|one|two|\d)",
               r"with (?:any|every|each) (?:drink|meal|main|item|bowl|order)s?(?: purchased)?", r"(?:drink|meal|main) purchase",
               r"min(?:imum)? (?:\d|two|three) (?:items|mains|drinks|bowls)")
GROUP = re.compile(r"(?<![\w])(?:min(?:imum)?\.? (?:of )?(?:\d|two|three|four) (?:pax|diners|adults|persons|people)|"
                   r"for (?:a )?(?:groups?|tables?) of (?:\d|two|three|four|five|six)|(?:\d|two|three|four) (?:paying )?(?:adults|diners|pax) or more|"
                   r"dine in (?:a )?(?:group|party) of|accompanied by (?:\d|one|two) paying)(?![\w])")
BOOKING = _rx(r"reservations? (?:is |are )?(?:required|needed|essential|recommended)", r"book(?:ing)? (?:in )?advance",
              r"advance (?:booking|reservation|order)s?", r"pre-?orders?", r"pre-?book", r"must (?:book|reserve)",
              r"(?:when|while) (?:making|you make) (?:a |your )?(?:reservation|booking)", r"book (?:online|via|through|a table)",
              r"(?:book|reserve) (?:via|through|on) (?:chope|quandoo|tablecheck|sevenrooms|eatigo)", r"chope", r"eatigo")
# An explicit cap only. "While stocks last" closes nearly every promo post, so it says nothing; a
# per-customer cap ("2 trays per customer") limits how much, not whether you get it.
FIRST_N = _rx(r"first \d+ (?:customers?|people|diners|pax|visitors?|guests?|orders?|redemptions?|shoppers?)",
              r"limited to (?:the first )?\d+ (?:customers?|redemptions?|people|pax|diners|sets daily|bowls daily)",
              r"\d+ (?:sets|bowls|servings|portions|pieces|cups|redemptions) (?:daily|a day|per day)",
              r"limited (?:servings|portions|slots) (?:daily|a day|per day)", r"daily limited")
SOCIAL = _rx(r"follow (?:us|our|them|their) (?:on )?(?:instagram|ig|facebook|fb|tiktok|telegram)?", r"like (?:and|&) share",
             r"share (?:this|the) post", r"tag (?:\d|two|three|a|your) friends?", r"comment below", r"story (?:and|&) tag",
             r"post a story", r"repost")
CODE = re.compile(r"(?<![\w])(?:promo ?codes?|(?:use|apply|enter|with) (?:the )?code|voucher codes?|coupon codes?|"
                  r"discount codes?|code [a-z0-9]{4,}|quote (?:the )?(?:code )?<[^>\n]{2,20}>|<[a-z0-9]{4,16}>)(?![\w])")
ONE_DAY = _rx(r"(?:today|tonight|one[- ]day|1[- ]day) only", r"this (?:mon|tues|wednes|thurs|fri|satur|sun)day only",
              r"for one day", r"one day only")
# A stated window of under SHORT_HOURS ("11AM - 12PM", "3pm-7pm") or happy hour. "10AM - 10PM" is
# just the opening hours.
HOURS = re.compile(r"(?<![\w])(?:happy hours?|(?:before|after) \d{1,2}(?:[:.]\d{2})?\s?(?:am|pm) only)(?![\w])")
TIME_RANGE = re.compile(r"(?<![\w:.])(\d{1,2})(?:[:.](\d{2}))?\s?(am|pm)?\s?(?:-|–|to)\s?(\d{1,2})(?:[:.](\d{2}))?\s?(am|pm)(?![\w])")
SHORT_HOURS = 6
_WD = r"(?:mon|tues?|wed(?:nes)?|thu(?:rs?)?|fri|sat(?:ur)?|sun)(?:day)?s?"
DAYS = re.compile(r"(?<![\w])(?:every (?:" + _WD + r")(?:\s?(?:&|and|,|-|to)\s?" + _WD + r")?|"
                  r"(?:mondays|tuesdays|wednesdays|thursdays|fridays|saturdays|sundays)|"
                  r"weekdays? only|weekends? only|on weekdays|\(weekdays?\)|weekdays? \d{1,2}(?:[:.]\d{2})?\s?(?:am|pm)|"
                  r"mon(?:day)?s?\s?(?:-|to)\s?(?:thu|fri)(?:rs|day)?s?|"
                  r"chicken tuesday)(?![\w])")
DELIVERY_ONLY = _rx(r"(?:via|on|through) (?:grabfood|foodpanda|deliveroo)", r"delivery only", r"for delivery orders?",
                    r"(?:grabfood|foodpanda|deliveroo)[- ]exclusive", r"delivery orders? only")

# Birthday perks already carry parsed needs (lobang.birthday); map them onto this vocabulary.
BDAY_NEEDS = {"member": "member", "app": "app", "min-spend": "min-spend", "group": "group", "booking": "booking",
              "id": None, "prior-purchase": "purchase"}


def _cost(tags, pct):
    """What the deal gives. "Buy-1-Get-1-FREE" is a 1-for-1, so that wins; "free" is the
    HEADLINE's word only (the caller passes it), because a body's "free wine tastings" or "free
    upsize" is a side perk, not the deal."""
    if "1-for-1" in tags:
        return "1-for-1"
    if "free" in tags:
        return "free"
    if pct or "pct-off" in tags:
        return "pct-off"
    if "cheap" in tags:
        return "cheap"
    return None


def _short(m):
    """A time range shorter than SHORT_HOURS. "12-6pm" takes the second meridiem for the first."""
    h1, m1, ap1, h2, m2, ap2 = m.groups()
    h1, h2 = int(h1), int(h2)
    if h1 > 12 or h2 > 12:
        return False
    ap1 = ap1 or ap2

    def mins(h, mi, ap):
        return (h % 12 + (12 if ap == "pm" else 0)) * 60 + int(mi or 0)

    a, b = mins(h1, m1, ap1), mins(h2, m2, ap2)
    if b <= a:
        b += 24 * 60
    return b - a < SHORT_HOURS * 60


BOILERPLATE = re.compile(r"visit [\w&' ]{2,60} for the full post\.?|t&cs? apply,? more info here|more info: \S+|"
                         r"find out more: \S+|@\w+ #\w+|\[\s*$")


def extract(title, text, tags=(), birthday=None, pct=None, valid=None):
    """Attributes of one deal. `title` is its headline, `text` the post's own words (summary + body),
    `valid` its (valid_from, valid_until): the same day twice is a one-day deal."""
    t_head = fold(title or "")
    body = fold(text or "")[:TEXT_MAX]
    hay = NEGATED.sub(" ", t_head + " \n " + body)
    tags = set(tags or ())
    needs = set()
    min_spend = None

    if CONTEST.search(hay):
        needs.add("contest")
    if ELIGIBLE.search(hay):
        needs.add("eligible")
    head = NEGATED.sub(" ", t_head)
    if CARD.search(head) or CARD_HEAD.search(head) or CARD_STRICT.search(hay):
        needs.add("card")
    if MEMBER_HEAD.search(head) or MEMBER.search(hay):
        needs.add("member")
    if APP.search(hay) and not APP_OPTIONAL.search(hay):
        needs.add("app")
    m = MIN_SPEND.search(hay)
    if m:
        needs.add("min-spend")
        min_spend = int(round(float(m.group(1))))
    elif MIN_SPEND_BARE.search(hay):
        needs.add("min-spend")
    free_head = bool(FREE.search(t_head)) and not NOT_FREE.search(t_head)
    given = (tags - {"free"}) | ({"free"} if free_head else set()) | ({"1-for-1"} if ONE_FOR_ONE.search(t_head) else set())
    cost_kind = _cost(given, pct or bool(PCT_OFF.search(t_head)))
    # "With any purchase" is a condition on a freebie or a discount. On a price deal ("smoothies
    # from $6.90") buying is the deal itself, and the body's "$39.90 bottle with any drink" is an add-on.
    if (PURCHASE.search(hay) and "min-spend" not in needs
            and (cost_kind in ("free", "pct-off") or PURCHASE.search(head))):
        needs.add("purchase")
    if GROUP.search(hay):
        needs.add("group")
    if BOOKING.search(hay):
        needs.add("booking")
    if FIRST_N.search(hay):
        needs.add("first-n")
    if SOCIAL.search(hay):
        needs.add("social")
    if CODE.search(hay):
        needs.add("code")
    if "ends-today" in tags or ONE_DAY.search(hay) or (valid and valid[0] and valid[0] == valid[1]):
        needs.add("one-day")
    if HOURS.search(hay) or any(_short(m) for m in TIME_RANGE.finditer(hay)):
        needs.add("hours")
    if DAYS.search(hay):
        needs.add("days")
    if DELIVERY_ONLY.search(hay) and not re.search(r"dine[- ]in|in-store|takeaway", hay):
        needs.add("delivery")
    # A "1-for-1" is itself a purchase (buy one, the second is free); listing it as a need would
    # charge every 1-for-1 twice for the same fact.
    if "1-for-1" in tags or ONE_FOR_ONE.search(t_head):
        needs.discard("purchase")
    if birthday:
        for n in birthday.get("needs") or []:
            if BDAY_NEEDS.get(n):
                needs.add(BDAY_NEEDS[n])
        if isinstance(birthday.get("min_spend"), int):
            min_spend = birthday["min_spend"]
            needs.add("min-spend")

    cost = 0
    for n in needs:
        c = COST[n]
        if n == "min-spend" and min_spend is not None:
            c = 6 if min_spend <= 15 else 12 if min_spend <= 50 else 20
        cost += c
    prices = [float(p) for p in PRICE.findall(t_head) if float(p) > 0]
    return {
        "cost": cost_kind,
        "price": min(prices) if prices else None,
        "needs": [n for n in NEEDS if n in needs],
        "min_spend": min_spend,
        # Boilerplate ("Visit Great Deals Singapore for the full post.") is not text to check.
        "checked": len(BOILERPLATE.sub("", body).strip()) >= CHECK_MIN,
        "ease": max(0, 100 - cost),
    }


def ease_points(a):
    """Hot-score adjustment for a promo, in [-25, +13].

    Centred on ease 88 (one membership sign-up) = 0, so nothing-asked is +8, a bank card -4, a
    lucky draw -22. A freebie with nothing asked is the best lobang there is: +5 more. A headline-only
    deal with no stated needs gets 0: unknown is not easy, and must not outrank a stated walk-in.
    "Free with any purchase" is not a freebie, so it gets no bonus."""
    if not a["checked"] and not a["needs"]:
        return 0
    pts = max(-25.0, min(8.0, (a["ease"] - 88) / 1.5))
    if (a["cost"] == "free" and a["ease"] >= 90 and a["checked"]
            and "purchase" not in a["needs"] and "min-spend" not in a["needs"]):
        pts += 5
    return int(round(pts))


# Used by the page's "Easy to claim" filter and by tests: what "easy" means, in one place.
EASY_MIN = 80


def is_easy(a):
    return a["checked"] and a["ease"] >= EASY_MIN and "contest" not in a["needs"]
