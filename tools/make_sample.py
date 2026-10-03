"""Write a dev sample public/deals.json relative to today's SG date."""
import json
import os
from datetime import datetime, timedelta, timezone

SGT = timezone(timedelta(hours=8))
now = datetime.now(SGT)
today = now.date()


def d(n):
    return (today + timedelta(days=n)).isoformat()


def iso(h):
    return (now - timedelta(hours=h)).isoformat(timespec='seconds')


def deal(i, kind, title, merchants, cat, tags, until, score, summary, links, origin=None, pct=None, frm=0, first=2, pubs=None):
    o = {
        'id': 'd_%010x' % (0x3f9a1c2b7e + i * 7919), 'kind': kind, 'title': title, 'merchants': merchants,
        'category': cat, 'tags': tags, 'origin': origin, 'valid_from': d(-frm), 'valid_until': until,
        'published': iso(first + 1), 'first_seen': iso(first), 'last_seen': iso(1), 'score': score,
        'summary': summary, 'publishers': pubs or len(links),
        'links': [{'publisher': p, 'url': u, 'title': title} for p, u in links],
    }
    if pct is not None:
        o['pct'] = pct
    return o


SP = 'https://example.com/singpromos/'
deals = [
    deal(1, 'promo', "McDonald's 1-for-1 McSpicy via app", ["McDonald's"], 'fast-food', ['1-for-1', 'app-only'], d(9), 92,
         'Buy one McSpicy meal and get another free when you order through the McDonald\'s app. Redeem once per account per day, dine-in or takeaway only.',
         [('SingPromos', SP + 'mcd'), ('MoneySmart', 'https://example.com/ms/mcd')], pubs=3),
    deal(2, 'opening', 'Tsujiri opens first Singapore flagship at Jewel', ['Tsujiri'], 'bubble-tea', ['overseas', 'first-in-sg', 'limited'], None, 88,
         'Kyoto matcha house since 1860 opens its first Singapore outlet, with an opening week free-drink giveaway for the first 100 guests daily.',
         [('Seth Lui', 'https://example.com/sl/tsujiri'), ('Eatbook', 'https://example.com/eb/tsujiri')], origin='Japan', frm=0, first=5),
    deal(3, 'promo', '50% off all large pizzas this weekend', ["Domino's"], 'fast-food', ['pct-off', 'delivery', 'ends-today'], d(0), 85,
         'Half-price large pizzas on delivery and pickup, today only. Min spend $25 for delivery.',
         [('SingPromos', SP + 'dominos')], pct=50),
    deal(4, 'promo', 'Free kopi with any breakfast set', ['Ya Kun Kaya Toast'], 'cafe', ['free', 'member'], d(21), 70,
         'Members get a free hot kopi or teh with any set before 11am on weekdays.',
         [('Ya Kun', 'https://example.com/yakun'), ('SingPromos', SP + 'yakun')]),
    deal(5, 'promo', 'Buffet lunch from $19.90++ with UOB cards', ['Spice Garden', 'Carousel'], 'buffet', ['card', 'buffet', 'cheap'], d(30), 66,
         'Weekday lunch buffet with UOB credit cards. Reservation recommended; not valid on public holidays.',
         [('MoneySmart', 'https://example.com/ms/buffet')], pubs=4),
    deal(6, 'opening', 'Gong Cha opens Tampines Hub kiosk', ['Gong Cha'], 'bubble-tea', ['limited'], None, 52,
         'New kiosk at Our Tampines Hub with opening promo: second cup 50% off all week.',
         [('Eatbook', 'https://example.com/eb/gongcha')], first=26),
    deal(7, 'opening', 'Korean fried chicken chain Kyochon returns with new Orchard outlet', ['Kyochon'], 'restaurant', ['overseas'], None, 74,
         'Soy garlic wings are back on Orchard Road. Outlet opens next month.',
         [('Seth Lui', 'https://example.com/sl/kyochon'), ('Eatbook', 'https://example.com/eb/kyochon')], origin='Korea', first=9),
    deal(8, 'promo', 'Starbucks: $2 off any Grande with app', ['Starbucks'], 'coffee', ['cheap', 'app-only'], d(4), 61,
         'Scan the app QR at the counter. One redemption per day.',
         [('SingPromos', SP + 'sbux')]),
    deal(9, 'promo', 'GrabFood free delivery on orders above $15', ['GrabFood'], 'delivery', ['free', 'delivery', 'limited'], d(2), 58,
         'Free delivery within 4km for orders above $15 with promo code on the app.',
         [('MoneySmart', 'https://example.com/ms/grab')]),
    deal(10, 'promo', 'Bundle: 8pc nuggets + fries + drink $6.90', ['Burger King'], 'fast-food', ['bundle'], None, 45,
         'Value bundle available at all outlets. Source does not state an end date.',
         [('SingPromos', SP + 'bk')]),
    deal(11, 'promo', "Bakery clearance: 30% off after 8pm", ['BreadTalk'], 'bakery-dessert', ['pct-off'], d(14), 40,
         'Selected breads 30% off after 8pm at participating outlets.',
         [('SingPromos', SP + 'breadtalk')], pct=30),
    deal(12, 'opening', 'Craft beer taproom Brewlander opens at Duxton', ['Brewlander'], 'bar-drinks', ['first-in-sg'], None, 38,
         'Twelve taps and a happy hour from 5 to 7pm, opening Friday.',
         [('Eatbook', 'https://example.com/eb/brewlander')], first=40),
    deal(13, 'promo', 'Hawker set meals from $4.50 at Maxwell', ['Tian Tian'], 'hawker', ['cheap'], None, 30,
         'Chicken rice set with soup and iced barley.',
         [('Seth Lui', 'https://example.com/sl/tiantian')]),
    deal(14, 'promo', 'Harvest of the week: 1-for-1 ramen on Wednesdays', ['Ippudo'], 'restaurant', ['1-for-1', 'overseas', 'card'], d(6), 77,
         'Show your card at the counter for a free second bowl of Shiromaru Motoaji.',
         [('MoneySmart', 'https://example.com/ms/ippudo')], origin='Japan'),
]
deals.sort(key=lambda x: -x['score'])

srcs = [
    ('singpromos', 'SingPromos', 'rss', True, 30, 18, None),
    ('moneysmart', 'MoneySmart', 'html', True, 22, 9, None),
    ('sethlui', 'Seth Lui', 'rss', True, 15, 15, None),
    ('eatbook', 'Eatbook', 'rss', True, 12, 12, None),
    ('hungrygowhere', 'HungryGoWhere', 'html', False, 0, 0, 'HTTP 403 Forbidden'),
    ('tabelog', 'Tabelog SG', 'html', False, 0, 0, 'Timed out after 15s'),
]
health = {
    'ok': sum(1 for s in srcs if s[3]), 'total': len(srcs),
    'sources': [{'name': n, 'publisher': p, 'type': t, 'ok': ok, 'count': c, 'fnb': f, 'error': e,
                 'last_ok': iso(2) if ok else None} for n, p, t, ok, c, f, e in srcs],
}
out = {'schema': 1, 'generated_at': iso(2), 'window_days': 21, 'health': health, 'deals': deals}
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public', 'deals.json')
with open(path, 'w', encoding='utf-8', newline='\n') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
    f.write('\n')
print('wrote', len(deals), 'deals')
