"""Customer birthday perks: is this one, and WHEN can it be redeemed. Deterministic, no LLM.

is_customer(title, summary, forced) -> bool
extract(text, redeem=None) -> dict   (see docs/contract.md, "birthday")

Two traps, both measured on live items (2026-10-03):
- A BRAND's birthday is not yours. "Penang Culture's Big Boss Birthday", "Soup Restaurant turns 35"
  and "Kris+ Birthday Bash" are ordinary promos, never birthday perks.
- Loose "free drink on your birthday" usually means the birthday MONTH: Mr. Coconut and LiHO
  both say it in prose and "Within birthday month" in their redeem line. So in prose only an
  explicit "actual birthday" / "birthday itself" / "only on your birthday" means the day; a loose
  one stays "unknown". A labelled redeem line ("Redeem on: On birthday.") is taken at its word.
"""

from __future__ import annotations

import re

from .classify import fold

WINDOWS = ("day", "around", "month", "month-plus", "week", "visit", "unknown")

_NUMS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
         "eight": 8, "nine": 9, "ten": 10, "fourteen": 14, "thirty": 30}
_N = r"(\d{1,2}|an?|one|two|three|four|five|six|seven|eight|nine|ten|fourteen|thirty)"
_UNIT = r"(days?|weeks?)"


def _num(s):
    return int(s) if s.isdigit() else _NUMS[s]


def _days(n, unit):
    return _num(n) * (7 if unit.startswith("week") else 1)


# ---- is it the customer's birthday? ------------------------------------------
CUST_STRONG = re.compile(r"your (?:actual )?birthday|birthday month|month of your birthday|birthday celebrants?"
                         r"|(?<![\w])celebrants?(?![\w])|birthday (?:boy|girl|person|babies|baby)"
                         r"|on (?:their|his|her) birthday")
CUST_WEAK = re.compile(r"birthday (?:treats?|perks?|rewards?|freebies?|vouchers?|gifts?|privileges?|discounts?"
                       r"|deals?|promos?|promotions?|specials?|cakes?|offers?)")
# In an excerpt, a birthday cue must sit next to a perk, or "perfect for your birthday" tags a review.
CUST_SUMMARY = re.compile(r"(?:free|complimentary|redeem|claim|enjoy|entitled|get)[^.]{0,60}(?:your birthday|birthday month)"
                          r"|(?:your birthday|birthday month)[^.]{0,40}(?:free|complimentary|voucher|discount|% off|1-for-1)")
BRAND = re.compile(r"\d+(?:st|nd|rd|th) birthday|turns \d+|birthday bash|anniversary|founder'?s? birthday"
                   r"|big boss birthday|(?:'s|its|their) (?:\w+ ){0,2}birthday (?:celebrations?|sale|party|special|menu)")


def is_customer(title, summary="", forced=False):
    """forced: the source only lists customer birthday perks (a birthday roundup)."""
    if forced:
        return True
    t, s = fold(title or ""), fold(summary or "")
    if CUST_STRONG.search(t):
        return True
    brand = BRAND.search(t) or BRAND.search(s)
    if brand:
        return False
    return bool(CUST_WEAK.search(t) or CUST_SUMMARY.search(s))


# ---- when ------------------------------------------------------------------------
_BD = r"(?:your |their |the )?(?:actual )?birthday"
VISIT = re.compile(r"day of (?:your )?(?:dining|dine-in|visit)|on the day (?:you|of) (?:dine|dining|visit)")
AROUND = re.compile(r"(?:up to |within )?" + _N + r"\s*" + _UNIT + r"\s*(?:before\s*(?:and/or|and|or|&|/)\s*after"
                    r"|either side)")
WITHIN_OF = re.compile(r"within\s*" + _N + r"\s*" + _UNIT + r"\s*of\s*" + _BD + r"(?!\s*month)")
MONTH_PLUS = re.compile(r"within\s*" + _N + r"\s*days?\s*of\s*(?:your\s*)?birthday month")
AFTER = re.compile(_BD + r"\s*(?:and|&|\+|plus)\s*(?:the\s*)?" + _N + r"\s*" + _UNIT + r"\s*(?:after|following)"
                   r"|(?:up to |within )" + _N + r"\s*" + _UNIT + r"\s*after\s*" + _BD)
DAY_STRICT = re.compile(r"actual birthday|exact birthday|birthday itself|on " + _BD + r" only|only on " + _BD
                        + r"|on the (?:day|date) of " + _BD + r"|valid (?:only )?on " + _BD + r"(?! month)")
# In a labelled redeem line, "On birthday." is the day.
DAY_LABEL = re.compile(r"^(?:on |only on )?" + _BD + r"(?:\s*(?:only|itself|date))?\s*\.?$")
WEEK = re.compile(r"birthday week|week of " + _BD)
MONTH = re.compile(r"birthday month|month of " + _BD + r"|birthday'?s? month")

_DOW = r"(?<![a-z])(mon|tue|wed|thu|fri|sat|sun)(?:day|sday|nesday|rsday|urday|s|r|rs)?\.?(?![a-z])"
DOW_RANGE = re.compile(_DOW + r"\s*(?:-|to)\s*" + _DOW)
WEEKDAYS = re.compile(r"(?<![\w])week ?days?(?![\w])")
WEEKENDS = re.compile(r"(?<![\w])week ?ends?(?![\w])")
EXCL_PH = re.compile(r"(?:except|excl(?:\.|uding|udes)?|not valid on|not applicable on)[^.]{0,40}?"
                     r"(?<![a-z])(?:ph|public holidays?)(?![a-z])")

# ---- conditions ----------------------------------------------------------------
NO_MEMBER = re.compile(r"(?:(?<![\w])no|without|don'?t (?:even )?need (?:a|any)|not need (?:a|any))\s+membership"
                       r"|membership (?:is )?not (?:required|needed)|no sign[- ]?ups?")
MEMBER = re.compile(r"(?<![\w])(?:members?(?:hip)?|sign(?:ing)? up|register|rewards? (?:programme|program|club|app)"
                    r"|loyalty|club|vibe card)(?![\w])")
MIN_SPEND = re.compile(r"(?<![\w])min(?:imum|\.)?\s*(?:spend|purchase)?\s*(?:of\s*)?s?\$\s?(\d{1,4})"
                       r"|with\s*s?\$\s?(\d{1,4})\s*(?:spent|spend|minimum spend|min\.? spend)"
                       r"|s?\$\s?(\d{1,4})\s*(?:min(?:imum)?\.?\s*spend|spent)")
GROUP = re.compile(r"(?:at least|minimum(?: of)?|min\.?|with)\s*" + _N + r"\s*(other\s*)?(paying\s*)?"
                   r"(?:adults?|people|diners|pax|persons|guests|friends)")
BOOKING = re.compile(r"reserv(?:e|ation|ations)|book(?:ing)?(?: a| the| your)? (?:table|in advance|ahead|online)"
                     r"|pre-?book|advance booking")
ID_PROOF = re.compile(r"photo id|(?<![\w])nric(?![\w])|singpass|proof of (?:birth|age|identity|birthday)|identification"
                      r"|(?<![\w])ic(?![\w])|(?<![\w])id(?![\w])")
APP = re.compile(r"(?<![\w])app(?![\w])")
PRIOR = re.compile(r"prior (?:transaction|purchase)|accrue|at least (?:one|1) (?:prior )?(?:transaction|purchase)"
                   r"|in the past (?:year|12 months)")
SIGNUP_LEAD = re.compile(r"(?:sign(?:ed)? up|register(?:ed)?|join(?:ed)?|be a member)[^.]{0,30}?" + _N + r"\+?\s*"
                         r"(days?|weeks?|months?)\s*(?:before|prior|in advance|ahead|earlier)")

def _sentence(text, pos):
    """The source's own sentence around pos, so the card can quote it rather than paraphrase."""
    start = max(text.rfind(". ", 0, pos), text.rfind("\n", 0, pos))
    end = text.find(". ", pos)
    s = text[start + 1 if start >= 0 else 0: end + 1 if end >= 0 else len(text)].strip()
    return s[:160]


def _window(t, labelled):
    """(window, before, after, match) from folded text, most specific first."""
    m = AROUND.search(t)
    if m:
        n = _days(m.group(1), m.group(2))
        return "around", n, n, m
    m = WITHIN_OF.search(t)
    if m:
        n = _days(m.group(1), m.group(2))
        return "around", n, n, m
    m = AFTER.search(t)
    if m:
        n, u = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        return "around", 0, _days(n, u), m
    m = MONTH_PLUS.search(t)
    if m:
        return "month-plus", 0, _num(m.group(1)), m
    m = DAY_STRICT.search(t) or (DAY_LABEL.search(t.strip()) if labelled else None)
    if m:
        return "day", 0, 0, m
    m = VISIT.search(t)
    if m:
        return "visit", 0, 0, m
    m = WEEK.search(t)
    if m:
        return "week", 0, 0, m
    m = MONTH.search(t)
    if m:
        return "month", 0, 0, m
    return "unknown", 0, 0, None


def extract(title, summary="", redeem=None):
    """redeem: a labelled "Redeem on:" line, which wins when it states a window."""
    raw = (title or "") + ". " + (summary or "")
    t = fold(raw)
    window, before, after, m, said = "unknown", 0, 0, None, None
    if redeem:
        r = fold(redeem)
        window, before, after, m = _window(r, True)
        if m:
            said = redeem.strip()[:160]
    if window == "unknown":
        window, before, after, m = _window(t, False)
        if m:
            said = _sentence(raw, m.start())
    scope = fold(redeem or "") + " \n " + t

    days = None
    dm = DOW_RANGE.search(fold(redeem or "")) or DOW_RANGE.search(t)
    if dm:
        days = dm.group(1).title() + "-" + dm.group(2).title()
    elif WEEKDAYS.search(scope):
        days = "Weekdays"
    elif WEEKENDS.search(scope):
        days = "Weekends"

    needs = []
    if MEMBER.search(t) and not NO_MEMBER.search(t):
        needs.append("member")
    if APP.search(t):
        needs.append("app")
    spend = None
    # Headline and redeem line only: Cedele's prose adds "a 15% off online voucher for a minimum
    # spend of $80", a second perk, and the $80 landed on the free cake.
    sm = MIN_SPEND.search(fold((title or "") + " \n " + (redeem or "")))
    if sm:
        spend = int(next(g for g in sm.groups() if g))
        needs.append("min-spend")
    group = None
    gm = GROUP.search(t)
    if gm:
        n = _num(gm.group(1))
        # "with 3 paying adults" / "3 other adults": the birthday person is extra.
        extra = 1 if (gm.group(2) or (gm.group(0).startswith("with") and gm.group(3))) else 0
        if n + extra >= 2:
            group = n + extra
            needs.append("group")
    if BOOKING.search(t):
        needs.append("booking")
    if ID_PROOF.search(t):
        needs.append("id")
    if PRIOR.search(t):
        needs.append("prior-purchase")
    lead = None
    lm = SIGNUP_LEAD.search(t)
    if lm:
        unit = lm.group(2)
        lead = _num(lm.group(1)) * (30 if unit.startswith("month") else 7 if unit.startswith("week") else 1)

    return {
        "window": window,
        "before": before,
        "after": after,
        "days": days,
        "excl_ph": bool(EXCL_PH.search(scope)),
        "needs": needs,
        "min_spend": spend,
        "group": group,
        "signup_days": lead,
        "said": said,
    }
