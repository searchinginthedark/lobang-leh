(function () {
  'use strict';

  var TZ = 'Asia/Singapore';
  var STALE_MS = 12 * 3600 * 1000;
  var KEY_PREFS = 'lobang:prefs';
  var KEY_SAVED = 'lobang:saved';
  var KEY_BDAY = 'lobang:bday';   // "MM-DD", no year; never leaves this browser
  var VIEWS = ['hot', 'ending', 'new', 'birthday', 'saved'];

  var CATS = {
    'fast-food': 'Fast food', 'coffee': 'Coffee', 'bubble-tea': 'Bubble tea',
    'bakery-dessert': 'Bakery & dessert', 'buffet': 'Buffet', 'restaurant': 'Restaurant',
    'cafe': 'Cafe', 'bar-drinks': 'Bar & drinks', 'hawker': 'Hawker', 'grocery': 'Grocery',
    'delivery': 'Delivery', 'other': 'Other'
  };

  // tag -> [label, css class]; unknown tags are ignored. Order = display order.
  var TAG_ORDER = ['ends-today', '1-for-1', 'pct-off', 'free', 'cheap', 'bundle', 'overseas',
    'first-in-sg', 'limited', 'app-only', 'card', 'member', 'delivery', 'buffet'];
  var TAG_CLASS = {
    'ends-today': 'b-warn', '1-for-1': 'b-deal', 'pct-off': 'b-deal', 'free': 'b-deal', 'cheap': 'b-deal',
    'overseas': 'b-good', 'first-in-sg': 'b-good', 'limited': 'b-warn'
  };

  var EMPTY = {
    hot: ['No deals match', 'Try clearing a filter or searching for something else.'],
    ending: ['Nothing with a stated end date', 'No matching deal states when it ends.'],
    'new': ['No new openings match', 'Check back later, or clear your filters.'],
    birthday: ['No birthday perks match', 'Try clearing a filter or searching for something else.'],
    saved: ['Nothing saved yet', 'Tap Save on a deal and it will show up here.']
  };

  // Colloquial regions (config/places.yml), in chip order.
  var AREAS = ['Central', 'East', 'North', 'North-East', 'West'];

  // Cards rendered per page. Hot held ~170 cards in one scroll; best-first means the
  // first page is the part worth reading, and "Show more" keeps the rest one tap away.
  var PAGE = 12;
  var state = { view: 'hot', q: '', cat: '', area: '', f1: false, free: false, shown: PAGE };
  var saved = {};
  var data = null;
  var loading = false;
  var autoTour = false;   // set by tourInit; consumed after the first load so cards exist
  var toastTimer = null;

  var $ = function (id) { return document.getElementById(id); };

  // ---------- storage (every access guarded) ----------
  function sGet(k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } }
  function sSet(k, v) { try { window.localStorage.setItem(k, v); } catch (e) { /* ignore */ } }

  function loadPrefs() {
    try {
      var p = JSON.parse(sGet(KEY_PREFS) || 'null');
      if (p && typeof p === 'object') {
        if (VIEWS.indexOf(p.view) >= 0) state.view = p.view;
        if (typeof p.q === 'string') state.q = p.q.slice(0, 100);
        if (typeof p.cat === 'string') state.cat = p.cat;
        if (AREAS.indexOf(p.area) >= 0) state.area = p.area;
        state.f1 = p.f1 === true;
        state.free = p.free === true;
      }
    } catch (e) { /* ignore */ }
    try {
      var s = JSON.parse(sGet(KEY_SAVED) || '[]');
      if (Array.isArray(s)) s.forEach(function (id) { if (typeof id === 'string') saved[id] = true; });
    } catch (e) { /* ignore */ }
  }
  function savePrefs() {
    sSet(KEY_PREFS, JSON.stringify({ view: state.view, q: state.q, cat: state.cat, area: state.area, f1: state.f1, free: state.free }));
  }
  function saveSaved() { sSet(KEY_SAVED, JSON.stringify(Object.keys(saved))); }

  // ---------- helpers ----------
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }

  function safeUrl(u) {
    try {
      var x = new URL(String(u));
      return (x.protocol === 'http:' || x.protocol === 'https:') ? x.href : null;
    } catch (e) { return null; }
  }

  var sgDay = new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' });
  function todaySG() { return sgDay.format(new Date()); }
  function dayNum(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '');
    return m ? Math.round(Date.UTC(+m[1], +m[2] - 1, +m[3]) / 86400000) : null;
  }
  function daysLeft(iso) {
    var a = dayNum(iso), b = dayNum(todaySG());
    return (a == null || b == null) ? null : a - b;
  }
  var dateFmt = new Intl.DateTimeFormat('en-GB', { timeZone: 'UTC', weekday: 'short', day: 'numeric', month: 'short' });
  function fmtDate(iso) {
    var n = dayNum(iso);
    if (n == null) return String(iso);
    var parts = dateFmt.formatToParts(new Date(n * 86400000)), o = {};
    parts.forEach(function (p) { o[p.type] = p.value; });
    return o.weekday + ' ' + o.day + ' ' + o.month;
  }
  function ago(ms) {
    var m = Math.max(0, Math.round(ms / 60000));
    if (m < 1) return 'just now';
    if (m < 60) return m + 'm ago';
    var h = Math.round(m / 60);
    if (h < 48) return h + 'h ago';
    return Math.round(h / 24) + 'd ago';
  }
  function ts(s) { var t = Date.parse(s); return isNaN(t) ? 0 : t; }

  function toast(msg) {
    var t = $('toast');
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove('show'); }, 2200);
  }

  // ---------- deal model ----------
  function tagsOf(d) { return Array.isArray(d.tags) ? d.tags : []; }
  function hasTag(d, t) { return tagsOf(d).indexOf(t) >= 0; }
  function merchantsOf(d) {
    return (Array.isArray(d.merchants) ? d.merchants : []).filter(function (m) { return typeof m === 'string' && m; });
  }

  // [{name, mrt, region}] as the collector wrote it; anything malformed is dropped, never shown.
  function placesOf(d) {
    return (Array.isArray(d.places) ? d.places : []).filter(function (p) {
      return p && typeof p.name === 'string' && p.name;
    });
  }
  // "Hougang Mall, Hougang MRT" / "Bugis" (the area itself) / "Joo Chiat" (no station nearby).
  function placeText(p) {
    return typeof p.mrt === 'string' && p.mrt && p.mrt !== p.name ? p.name + ', ' + p.mrt + ' MRT' : p.name;
  }

  function badgesFor(d) {
    var out = [];
    var left = d.valid_until ? daysLeft(d.valid_until) : null;
    var tags = tagsOf(d);
    TAG_ORDER.forEach(function (t) {
      var label = null;
      var has = tags.indexOf(t) >= 0;
      if (t === 'ends-today') { if (has || left === 0) label = 'Ends today'; }
      else if (!has) return;
      else if (t === '1-for-1') label = '1-for-1';
      else if (t === 'pct-off') label = (typeof d.pct === 'number' ? d.pct : '') + (typeof d.pct === 'number' ? '% off' : 'Discount');
      else if (t === 'free') label = 'Free';
      else if (t === 'cheap') label = 'Under $5';
      else if (t === 'bundle') label = 'Bundle';
      else if (t === 'overseas') label = 'Overseas brand';
      else if (t === 'first-in-sg') label = 'First in SG';
      else if (t === 'limited') label = 'Limited';
      else if (t === 'app-only') label = 'App only';
      else if (t === 'card') label = 'Card deal';
      else if (t === 'member') label = 'Members';
      else if (t === 'delivery') label = 'Delivery';
      else if (t === 'buffet') label = 'Buffet';
      if (label) out.push([label, TAG_CLASS[t] || '']);
      if (t === 'overseas' && typeof d.origin === 'string' && d.origin) out.push(['from ' + d.origin, 'b-good']);
    });
    if (d.origin && !hasTag(d, 'overseas') && typeof d.origin === 'string') out.push(['from ' + d.origin, 'b-good']);
    return out;
  }

  // null when the source states no end date: an empty line beats a guess.
  function validity(d) {
    if (!d.valid_until) return null;
    var left = daysLeft(d.valid_until);
    if (left === 0 || hasTag(d, 'ends-today')) return { text: 'Ends today', cls: 'today' };
    var s = 'Till ' + fmtDate(d.valid_until);
    if (left != null && left > 0) s += ' · ' + left + (left === 1 ? ' day left' : ' days left');
    return { text: s, cls: '' };
  }

  // ---------- birthday perks (docs/contract.md, "birthday") ----------
  var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
    'October', 'November', 'December'];
  var MDAYS = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

  function bdayGet() {
    var m = /^(\d\d)-(\d\d)$/.exec(sGet(KEY_BDAY) || '');
    if (!m) return null;
    var mm = +m[1], dd = +m[2];
    return (mm >= 1 && mm <= 12 && dd >= 1 && dd <= MDAYS[mm - 1]) ? { m: mm, d: dd } : null;
  }
  function dn(y, m, d) { return Math.round(Date.UTC(y, m - 1, d) / 86400000); }
  function leap(y) { return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0; }
  // A window that already passed this year shows next year's dates, so those carry the year.
  function fmtDn(n) {
    var iso = new Date(n * 86400000).toISOString().slice(0, 10);
    return fmtDate(iso) + (iso.slice(0, 4) !== todaySG().slice(0, 4) ? ' ' + iso.slice(0, 4) : '');
  }
  function plural(n, w) { return n + ' ' + w + (n === 1 ? '' : 's'); }

  // [first, last] day numbers of a perk's window for a birthday in year y; null when the source
  // gives no date rule (week, visit, unknown). A 29 Feb birthday counts as 28 Feb in other years.
  function windowIn(b, bd, y) {
    var B = dn(y, bd.m, bd.m === 2 && bd.d === 29 && !leap(y) ? 28 : bd.d);
    var M1 = dn(y, bd.m, 1), before = +b.before || 0, after = +b.after || 0;
    if (b.window === 'day') return [B, B];
    if (b.window === 'around') return [B - before, B + after];
    if (b.window === 'month') return [M1, dn(y, bd.m + 1, 1) - 1];   // Date.UTC rolls month 13 into January
    if (b.window === 'month-plus') return [M1, M1 + Math.max(1, after) - 1];
    return null;
  }
  // The next window that has not ended yet. Last year's is checked too: a 30 Dec birthday with
  // 14 days after is still claimable on 5 Jan.
  function bdayRange(b, bd) {
    if (!b || !bd) return null;
    var t = todaySG(), today = dayNum(t), y = +t.slice(0, 4);
    for (var k = -1; k <= 1; k++) {
      var r = windowIn(b, bd, y + k);
      if (!r) return null;
      if (r[1] >= today) return { start: r[0], end: r[1], now: r[0] <= today, left: r[1] - today };
    }
    return null;
  }

  function windowLabel(b) {
    var before = +b.before || 0, after = +b.after || 0;
    if (b.window === 'day') return 'On your birthday only';
    if (b.window === 'around') {
      if (before === after) return 'Up to ' + plural(before, 'day') + ' either side of your birthday';
      if (!before) return 'Your birthday and ' + plural(after, 'day') + ' after';
      if (!after) return plural(before, 'day') + ' before your birthday';
      return plural(before, 'day') + ' before to ' + plural(after, 'day') + ' after your birthday';
    }
    if (b.window === 'month') return 'Any day in your birthday month';
    if (b.window === 'month-plus') return plural(after, 'day') + ' from the 1st of your birthday month';
    if (b.window === 'week') return 'Your birthday week';
    if (b.window === 'visit') return 'On the day you dine in, tell the staff';
    return 'Claim window not stated';
  }

  function bdayWhen(b, r) {
    var s = windowLabel(b);
    if (!r) return { text: s, cls: b.window === 'unknown' ? 'muted' : '' };
    if (r.now) {
      return { text: s + ' · Claim now, ' + (r.left === 0 ? 'last day today' : 'till ' + fmtDn(r.end)), cls: 'now' };
    }
    return { text: s + ' · ' + (r.start === r.end ? 'On ' + fmtDn(r.start) : fmtDn(r.start) + ' to ' + fmtDn(r.end)), cls: '' };
  }

  function bdayNeeds(b) {
    var n = Array.isArray(b.needs) ? b.needs : [], out = [];
    if (typeof b.days === 'string' && b.days) out.push(b.days + ' only');
    if (b.excl_ph) out.push('not on public holidays');
    if (n.indexOf('member') >= 0) out.push('members');
    if (n.indexOf('app') >= 0) out.push('via app');
    if (typeof b.signup_days === 'number') out.push('join ' + plural(b.signup_days, 'day') + ' ahead');
    if (typeof b.min_spend === 'number') out.push('min spend $' + b.min_spend);
    else if (n.indexOf('min-spend') >= 0) out.push('min spend');
    if (typeof b.group === 'number') out.push('group of ' + b.group + '+');
    if (n.indexOf('booking') >= 0) out.push('book ahead');
    if (n.indexOf('id') >= 0) out.push('bring ID');
    if (n.indexOf('prior-purchase') >= 0) out.push('needs an earlier purchase');
    if (!out.length) return null;
    var s = out.join(' · ');
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  // Claimable now (ending soonest), then upcoming (starting soonest), then no date rule (best first).
  function sortBirthday(list) {
    var bd = bdayGet();
    var keyed = list.map(function (d) { return { d: d, r: bdayRange(d.birthday, bd) }; });
    keyed.sort(function (a, b) {
      var ra = a.r ? (a.r.now ? 0 : 1) : 2, rb = b.r ? (b.r.now ? 0 : 1) : 2;
      if (ra !== rb) return ra - rb;
      if (ra === 0 && a.r.end !== b.r.end) return a.r.end - b.r.end;
      if (ra === 1 && a.r.start !== b.r.start) return a.r.start - b.r.start;
      return (b.d.score || 0) - (a.d.score || 0);
    });
    return keyed.map(function (k) { return k.d; });
  }

  function renderBday() {
    // Only the hint: the selects are the user's, synced from storage once in init(),
    // or picking a month before a day would be wiped by the next render.
    var bd = bdayGet(), hint = $('bday-hint');
    if (!bd) {
      hint.textContent = $('bday-m').value ? 'Now pick the day.' : 'Pick your birthday to see which perks you can claim now.';
      return;
    }
    var all = ((data && data.deals) || []).filter(function (x) { return hasTag(x, 'birthday'); });
    var now = all.filter(function (x) { var r = bdayRange(x.birthday, bd); return r && r.now; }).length;
    hint.textContent = now ? plural(now, 'perk') + ' you can claim today, listed first.'
      : 'None claimable today. Perks are listed by when they open.';
  }
  function fillDays(month) {
    var d = $('bday-d'), keep = d.value, max = month ? MDAYS[month - 1] : 31;
    while (d.options.length > 1) d.remove(1);
    for (var i = 1; i <= max; i++) d.add(new Option(String(i), String(i)));
    if (+keep <= max) d.value = keep;
  }
  function bdaySet() {
    var m = +$('bday-m').value, d = +$('bday-d').value;
    if (m && d && d <= MDAYS[m - 1]) sSet(KEY_BDAY, (m < 10 ? '0' : '') + m + '-' + (d < 10 ? '0' : '') + d);
    else { try { window.localStorage.removeItem(KEY_BDAY); } catch (e) { /* ignore */ } }
  }

  // ---------- open counter (fleet UX audit, 2026-10-08) ----------
  // "Do I still use this, and which views?" measured, not guessed. Calendar days (SGT) the app
  // came to the foreground, and the days each view was looked at; 60 days kept, never sent
  // anywhere. Same shape as curfew.opens.v1. A resume counts too, at most once per 30 minutes.
  var KEY_OPENS = 'lobang:opens';   // {"YYYY-MM-DD": opens}
  var KEY_VIEWS = 'lobang:views';   // {"YYYY-MM-DD": ["hot", "birthday", ...]}
  var OPEN_DAYS = 60;
  var OPEN_GAP = 30 * 60 * 1000;
  var lastOpen = 0;

  function readObj(k) {
    try { var o = JSON.parse(sGet(k) || '{}'); return o && typeof o === 'object' && !Array.isArray(o) ? o : {}; }
    catch (e) { return {}; }
  }
  function trimDays(o) {
    var cutoff = sgDay.format(new Date(Date.now() - OPEN_DAYS * 86400000));
    Object.keys(o).forEach(function (k) { if (k < cutoff) delete o[k]; });
    return o;
  }
  function countOpen() {
    var now = Date.now();
    if (now - lastOpen < OPEN_GAP) return;
    lastOpen = now;
    var o = trimDays(readObj(KEY_OPENS)), t = todaySG();
    o[t] = (+o[t] || 0) + 1;
    sSet(KEY_OPENS, JSON.stringify(o));
  }
  function countView(v) {
    var o = trimDays(readObj(KEY_VIEWS)), t = todaySG();
    var day = Array.isArray(o[t]) ? o[t] : [];
    if (day.indexOf(v) < 0) day.push(v);
    o[t] = day;
    sSet(KEY_VIEWS, JSON.stringify(o));
  }
  function usageText() {
    var opens = Object.keys(trimDays(readObj(KEY_OPENS))).length, views = trimDays(readObj(KEY_VIEWS));
    var per = {}, names = { hot: 'Hot', ending: 'Ending soon', 'new': 'New openings', birthday: 'Birthday', saved: 'Saved' };
    Object.keys(views).forEach(function (d) {
      (Array.isArray(views[d]) ? views[d] : []).forEach(function (v) { per[v] = (per[v] || 0) + 1; });
    });
    return 'Opened on ' + opens + ' of the last ' + OPEN_DAYS + ' days. Days each view was used: ' +
      VIEWS.map(function (v) { return names[v] + ' ' + (per[v] || 0); }).join(', ') +
      '. Counted on this phone only, never sent.';
  }

  // ---------- filtering / views ----------
  function matches(d) {
    if (state.cat && d.category !== state.cat) return false;
    if (state.area && !placesOf(d).some(function (p) { return p.region === state.area; })) return false;
    if (state.f1 && !hasTag(d, '1-for-1')) return false;
    if (state.free && !hasTag(d, 'free')) return false;
    var q = state.q.trim().toLowerCase();
    if (q) {
      var where = placesOf(d).map(function (p) { return p.name + ' ' + (p.mrt || ''); }).join(' ');
      var hay = (merchantsOf(d).join(' ') + ' ' + (d.title || '') + ' ' + (d.summary || '') + ' ' + where).toLowerCase();
      if (hay.indexOf(q) < 0) return false;
    }
    return true;
  }

  function selectDeals() {
    var all = (data && data.deals) || [];
    var list = all.filter(matches);
    if (state.view === 'hot') {
      // Birthday perks are standing offers, not news: they live in their own view.
      list = list.filter(function (d) { return !hasTag(d, 'birthday'); });
    } else if (state.view === 'birthday') {
      list = sortBirthday(list.filter(function (d) { return hasTag(d, 'birthday'); }));
    } else if (state.view === 'ending') {
      list = list.filter(function (d) { return !!d.valid_until; });
      list.sort(function (a, b) {
        return a.valid_until < b.valid_until ? -1 : a.valid_until > b.valid_until ? 1 : (b.score || 0) - (a.score || 0);
      });
    } else if (state.view === 'new') {
      list = list.filter(function (d) { return d.kind === 'opening'; });
      list.sort(function (a, b) { return ts(b.first_seen) - ts(a.first_seen); });
    } else if (state.view === 'saved') {
      list = list.filter(function (d) { return saved[d.id]; });
    }
    return list;
  }

  // ---------- rendering ----------
  function card(d) {
    var c = el('article', 'card' + (d.kind === 'opening' ? ' opening' : ''));
    // The headline is always the heading; a known merchant rides in the eyebrow, an unknown
    // one is simply left out, so every card has the same shape.
    var merch = merchantsOf(d);
    var eb = el('div', 'eyebrow');
    var bday = hasTag(d, 'birthday') && d.birthday && typeof d.birthday === 'object' ? d.birthday : null;
    eb.appendChild(el('span', 'kind', d.kind === 'opening' ? 'New opening' : bday ? 'Birthday' : 'Promo'));
    if (merch.length) eb.appendChild(el('span', 'merch', merch.join(' + ')));
    c.appendChild(eb);
    c.appendChild(el('h2', 'title', d.title || merch.join(' + ') || 'Untitled'));
    // Only when the post names the place; a chain-wide deal has none, and none is never guessed.
    var ps = placesOf(d);
    if (ps.length) {
      var wh = el('p', 'where');
      wh.appendChild(el('span', 'sr', 'Where: '));
      wh.appendChild(document.createTextNode(ps.map(placeText).join(' · ')));
      c.appendChild(wh);
    }

    var bs = badgesFor(d);
    if (bs.length) {
      var ul = el('ul', 'badges');
      bs.forEach(function (b) { ul.appendChild(el('li', 'badge ' + b[1], b[0])); });
      c.appendChild(ul);
    }

    var v = validity(d);
    if (v) c.appendChild(el('p', 'valid ' + v.cls, v.text));
    if (bday) {
      var w = bdayWhen(bday, bdayRange(bday, bdayGet()));
      c.appendChild(el('p', 'valid bday-when ' + w.cls, w.text));
      var needs = bdayNeeds(bday);
      if (needs) c.appendChild(el('p', 'bday-needs', needs));
      // The source's own words: roundups disagree on the same brand, and blackout dates live here.
      if (typeof bday.said === 'string' && bday.said) c.appendChild(el('p', 'bday-said', 'Source says: “' + bday.said + '”'));
    }

    if (d.summary) {
      var sb = el('button', 'summary-btn');
      sb.type = 'button';
      sb.setAttribute('aria-expanded', 'false');
      sb.appendChild(el('span', 'summary', d.summary));
      sb.addEventListener('click', function () {
        sb.setAttribute('aria-expanded', sb.getAttribute('aria-expanded') === 'true' ? 'false' : 'true');
      });
      c.appendChild(sb);
    }

    var links = (Array.isArray(d.links) ? d.links : []).map(function (l) {
      return { url: l && safeUrl(l.url), pub: l && l.publisher, title: l && l.title };
    }).filter(function (l) { return l.url; });
    var total = Math.max(typeof d.publishers === 'number' ? d.publishers : 0, links.length);

    // One footer row: the newest source as the read link, "+N" for the rest, then actions.
    var act = el('div', 'actions');
    var list = null;
    if (links.length) {
      act.appendChild(srcLink(links[0], 'src'));
      if (total > 1) {
        var mb = el('button', 'more-btn', '+' + (total - 1));
        mb.type = 'button';
        mb.setAttribute('aria-expanded', 'false');
        mb.setAttribute('aria-label', (total - 1) + ' more source' + (total > 2 ? 's' : ''));
        list = el('ul', 'src-list');
        list.hidden = true;
        links.slice(1).forEach(function (l) {
          var li = el('li');
          li.appendChild(srcLink(l, null));
          list.appendChild(li);
        });
        if (total > links.length) list.appendChild(el('li', 'src-extra', '+' + (total - links.length) + ' not listed'));
        mb.addEventListener('click', function () {
          var open = mb.getAttribute('aria-expanded') !== 'true';
          mb.setAttribute('aria-expanded', String(open));
          list.hidden = !open;
        });
        act.appendChild(mb);
      }
    } else {
      act.appendChild(el('span', 'src'));
    }
    var isSaved = !!saved[d.id];
    var sv = el('button', 'act', isSaved ? 'Saved' : 'Save');
    sv.type = 'button';
    sv.setAttribute('aria-pressed', String(isSaved));
    sv.addEventListener('click', function () {
      if (saved[d.id]) delete saved[d.id]; else saved[d.id] = true;
      saveSaved();
      render();
    });
    var sh = el('button', 'act', 'Share');
    sh.type = 'button';
    sh.addEventListener('click', function () { share(d, links[0] && links[0].url); });
    act.appendChild(sv);
    act.appendChild(sh);
    c.appendChild(act);
    if (list) c.appendChild(list);
    return c;
  }

  function srcLink(l, cls) {
    var a = el('a', cls, (l.pub || new URL(l.url).hostname) + ' ↗');
    a.href = l.url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.title = l.title ? 'Read on ' + (l.pub || 'source') + ': ' + l.title : 'Read on source';
    return a;
  }

  function share(d, url) {
    var link = url || location.href;
    var title = d.title || merchantsOf(d).join(' + ') || 'LobangLeh deal';
    if (navigator.share) {
      navigator.share({ title: title, text: title, url: link }).catch(function () { /* cancelled */ });
      return;
    }
    var done = function () { toast('Link copied'); };
    var fail = function () { toast('Could not copy the link'); };
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(link).then(done, fail);
      else fail();
    } catch (e) { fail(); }
  }

  function showState(kind, head, body, withRetry) {
    var s = $('state');
    clear(s);
    s.className = 'state' + (kind === 'err' ? ' err' : '');
    s.appendChild(el('strong', null, head));
    s.appendChild(el('span', null, body));
    if (withRetry) {
      var b = el('button', 'icon-btn', 'Try again');
      b.type = 'button';
      b.addEventListener('click', load);
      s.appendChild(b);
    }
    s.hidden = false;
  }

  function healthOpen(open) {
    $('health-btn').setAttribute('aria-expanded', String(open));
    $('health-list').hidden = !open;
  }

  function renderHeader() {
    var fresh = $('fresh-text'), stale = $('stale');
    var h = $('health-btn');
    if (!data) { h.hidden = true; healthOpen(false); stale.hidden = true; return; }
    var t = ts(data.generated_at);
    if (t) {
      var age = Date.now() - t;
      fresh.textContent = 'Updated ' + ago(age);
      stale.hidden = age <= STALE_MS;
    } else {
      fresh.textContent = 'Update time unknown';
      stale.hidden = false;
    }
    var hl = data.health;
    if (hl && typeof hl === 'object') {
      h.hidden = false;
      h.textContent = hl.ok + '/' + hl.total + ' sources';
      var ul = $('health-list');
      clear(ul);
      (Array.isArray(hl.sources) ? hl.sources : []).forEach(function (s) {
        var li = el('li');
        li.appendChild(el('span', 'h-name', s.publisher || s.name || 'source'));
        li.appendChild(el('span', 'badge ' + (s.ok ? 'b-good' : 'b-deal'), s.ok ? 'ok' : 'error'));
        if (s.ok && typeof s.count === 'number') li.appendChild(el('span', null, s.count + ' items'));
        if (!s.ok && s.error) li.appendChild(el('span', 'h-err', String(s.error)));
        ul.appendChild(li);
      });
      ul.appendChild(el('li', 'h-usage', usageText()));
    } else {
      h.hidden = true;
      healthOpen(false);
    }
  }

  function renderChips() {
    var box = $('chips');
    clear(box);
    var seen = {};
    ((data && data.deals) || []).forEach(function (d) { if (d.category) seen[d.category] = true; });
    if (state.cat && !seen[state.cat]) state.cat = '';
    Object.keys(CATS).filter(function (k) { return seen[k]; }).forEach(function (k) {
      var b = el('button', 'chip', CATS[k]);
      b.type = 'button';
      b.setAttribute('aria-pressed', String(state.cat === k));
      b.addEventListener('click', function () {
        state.cat = state.cat === k ? '' : k;
        savePrefs();
        renderChips();
        rerender();
      });
      box.appendChild(b);
    });
    // Areas: only regions some card is in. A chain-wide promo names no place, so it never shows
    // under an area; the Showing line says so.
    var abox = $('areas');
    clear(abox);
    var inArea = {};
    ((data && data.deals) || []).forEach(function (d) { placesOf(d).forEach(function (p) { inArea[p.region] = true; }); });
    if (state.area && !inArea[state.area]) state.area = '';
    AREAS.filter(function (a) { return inArea[a]; }).forEach(function (a) {
      var b = el('button', 'chip', a);
      b.type = 'button';
      b.setAttribute('aria-pressed', String(state.area === a));
      b.addEventListener('click', function () {
        state.area = state.area === a ? '' : a;
        savePrefs();
        renderChips();
        rerender();
      });
      abox.appendChild(b);
    });
    abox.hidden = !abox.firstChild;
  }

  function renderControls() {
    Array.prototype.forEach.call(document.querySelectorAll('.tab'), function (t) {
      t.setAttribute('aria-selected', String(t.getAttribute('data-view') === state.view));
    });
    $('t-1for1').setAttribute('aria-pressed', String(state.f1));
    $('t-free').setAttribute('aria-pressed', String(state.free));
    // The panel is usually shut, so an active filter is always named above the list: a
    // filtered feed must never pass for a thin one.
    var on = [];
    if (state.cat) on.push(CATS[state.cat] || state.cat);
    if (state.area) on.push(state.area + ' (named places only)');
    if (state.f1) on.push('1-for-1');
    if (state.free) on.push('Free');
    if (state.q.trim()) on.push('“' + state.q.trim() + '”');
    var fb = $('filter-btn');
    fb.textContent = on.length ? 'Filter · ' + on.length : 'Filter';
    fb.classList.toggle('on', on.length > 0);
    fb.setAttribute('aria-label', on.length ? 'Filter, ' + on.length + ' on' : 'Filter');
    $('active').hidden = !on.length;
    $('active-text').textContent = 'Showing: ' + on.join(' · ');
    $('bday-box').hidden = state.view !== 'birthday';
    if (state.view === 'birthday') renderBday();
  }

  function render() {
    renderControls();
    var list = $('list');
    clear(list);
    $('state').hidden = true;
    if (!data) return;
    var deals = selectDeals();
    if (!deals.length) {
      var e = EMPTY[state.view];
      showState('empty', e[0], e[1], false);
      return;
    }
    var frag = document.createDocumentFragment();
    deals.slice(0, state.shown).forEach(function (d, i) {
      var c = card(d);
      if (i === 0) {
        // Tour targets (index.html #tour-steps).
        c.id = 'tour-first-card';
        c.querySelector('.actions').id = 'tour-first-actions';
      }
      frag.appendChild(c);
    });
    var left = deals.length - state.shown;
    if (left > 0) {
      var more = el('button', 'show-more', 'Show ' + Math.min(PAGE, left) + ' more · ' + left + ' left');
      more.id = 'tour-more';
      more.type = 'button';
      more.addEventListener('click', function () {
        var first = state.shown;
        state.shown += PAGE;
        render();
        // The button is gone; put focus on the first new card so keyboard users keep their place.
        var n = list.children[first];
        if (n) { n.tabIndex = -1; n.focus({ preventScroll: true }); }
      });
      frag.appendChild(more);
    }
    list.appendChild(frag);
  }

  // Any change to what the list shows starts again at page one.
  function rerender() {
    state.shown = PAGE;
    render();
  }

  // ---------- loading ----------
  function load() {
    if (loading) return;
    loading = true;
    var btn = $('refresh');
    btn.disabled = true;
    fetch('./deals.json', { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (j) {
      if (!j || !Array.isArray(j.deals)) throw new Error('Unexpected file format');
      j.deals = j.deals.filter(function (d) { return d && typeof d === 'object' && typeof d.id === 'string'; });
      data = j;
      renderHeader();
      renderChips();
      render();
    }).catch(function (err) {
      if (data) {
        toast('Refresh failed, showing older deals');
      } else {
        $('list').textContent = '';
        $('fresh-text').textContent = 'Could not load deals';
        $('stale').hidden = true;
        $('health-btn').hidden = true;
        healthOpen(false);
        showState('err', 'Could not load deals',
          'The deals file did not load (' + (err && err.message ? err.message : 'network error') + '). This is a loading problem, not an empty list.', true);
      }
    }).then(function () {
      loading = false;
      btn.disabled = false;
      if (autoTour) { autoTour = false; tourOpen(); }
    });
  }

  // ---------- guided tour ----------
  // Adapted from news-radar (2026-10-03). The steps are hidden <li>s in index.html, each naming
  // a target id and the view it lives on, so this code is generic. A step whose target is
  // missing or hidden is skipped: an empty filter result means fewer steps, never a broken tour.
  // It opens itself on a new visit (20 min apart) until "Do not show again" is ticked (saved the
  // moment it is ticked), "?" replays it, and it ends on the view it began on. Views change by
  // clicking the real tab buttons, so the tour exercises the same path a user does.
  var TOUR_GAP = 20 * 60 * 1000;
  var KEY_TOUR = 'lobang:tour';
  var KEY_SEEN = 'lobang:seen';
  var tour = { at: -1, from: 'hot', back: null, raf: 0, counted: [], steps: [], clicking: false };

  function tourTarget(k) {
    var id = tour.steps[k].getAttribute('data-target');
    return id ? $(id) : null;
  }
  function toView(v) {
    if (v && v !== state.view) {
      var b = document.querySelector('.tab[data-view="' + v + '"]');
      // Flagged so the open counter does not log the tour's own tab switches as use.
      if (b) { tour.clicking = true; b.click(); tour.clicking = false; }
    }
  }
  // Can step k show right now? Switches to its view first, since list targets only exist there.
  function tourUsable(k) {
    var li = tour.steps[k];
    if (!li.getAttribute('data-target')) return true;
    toView(li.getAttribute('data-view'));
    var t = tourTarget(k);
    return !!t && !t.closest('[hidden]');
  }
  // The card takes the half of the screen the target is not in.
  function tourSide(top, h, vh) { return top + h / 2 < vh / 2 ? 'bottom' : 'top'; }

  function tourPaint() {
    tour.raf = 0;
    if (tour.at < 0) return;
    var spot = $('tour-spot'), cardEl = $('tour-card');
    var t = tourTarget(tour.at), vh = window.innerHeight;
    if (!t) { spot.style.cssText = ''; cardEl.className = 'tour-card mid'; return; }
    var r = t.getBoundingClientRect(), h = Math.min(r.height, vh * 0.45), pad = 6;
    // Kept 2px inside the screen, or an edge target loses part of its outline.
    var vw = document.documentElement.clientWidth || window.innerWidth;
    var L = Math.max(2, r.left - pad), T = Math.max(2, r.top - pad);
    var R = Math.min(vw - 2, r.right + pad), B = Math.min(vh - 2, r.top + h + pad);
    spot.style.left = L + 'px';
    spot.style.top = T + 'px';
    spot.style.width = Math.max(0, R - L) + 'px';
    spot.style.height = Math.max(0, B - T) + 'px';
    cardEl.className = 'tour-card ' + tourSide(r.top, h, vh);
  }
  function tourLater() { if (tour.at >= 0 && !tour.raf) tour.raf = requestAnimationFrame(tourPaint); }

  function tourShow(i) {
    var k = tour.counted[i];
    tour.at = k;
    tourUsable(k);   // for its side effect: switch to the step's view
    var li = tour.steps[k], b = li.querySelector('b'), s = li.querySelector('span');
    $('tour-n').textContent = (i + 1) + ' of ' + tour.counted.length;
    $('tour-t').textContent = b ? b.textContent : '';
    $('tour-b').textContent = s ? s.textContent : '';
    $('tour-back').hidden = i === 0;
    $('tour-next').textContent = i === tour.counted.length - 1 ? 'Done' : 'Next';
    var t = tourTarget(k);
    // A target in the page scrolls to the top fifth so the card fits below it. The sticky
    // header targets sit at the top anyway.
    if (t) {
      var y = t.getBoundingClientRect().top + (window.pageYOffset || 0) - window.innerHeight * 0.2;
      window.scrollTo(0, Math.max(0, y));
    }
    tourPaint();
    $('tour-next').focus();
  }

  function tourClose() {
    if (tour.at < 0) return;
    tour.at = -1;
    $('tour').hidden = true;
    toView(tour.from);
    window.scrollTo(0, 0);
    if (tour.back && tour.back.focus) tour.back.focus();
  }

  function tourOpen() {
    if (tour.at >= 0 || !tour.steps.length) return;
    tour.from = state.view;
    // A tap does not focus a button on iOS/Safari, so "nothing focused" returns to "?".
    var ae = document.activeElement;
    tour.back = ae && ae !== document.body ? ae : $('tourbtn');
    // Which steps can show is decided once, up front, so "3 of 7" never changes mid-tour.
    tour.counted = [];
    for (var k = 0; k < tour.steps.length; k++) if (tourUsable(k)) tour.counted.push(k);
    toView(tour.from);
    if (!tour.counted.length) return;
    $('tour-off').checked = sGet(KEY_TOUR) === 'off';
    $('tour').hidden = false;
    tourShow(0);
  }

  function tourStep(d) {
    var i = tour.counted.indexOf(tour.at) + d;
    if (i >= tour.counted.length) tourClose();
    else if (i >= 0) tourShow(i);
  }

  // Returns whether the tour should open itself once the deals have loaded.
  function tourInit() {
    tour.steps = [].slice.call(document.querySelectorAll('#tour-steps li'));
    if (!tour.steps.length) return false;
    $('tour-next').addEventListener('click', function () { tourStep(1); });
    $('tour-back').addEventListener('click', function () { tourStep(-1); });
    $('tour-skip').addEventListener('click', tourClose);
    $('tour-off').addEventListener('change', function (e) {
      if (e.target.checked) sSet(KEY_TOUR, 'off');
      else { try { window.localStorage.removeItem(KEY_TOUR); } catch (err) { /* ignore */ } }
    });
    // On the document, not the card: a tap on the dim moves focus out of the card, and Esc
    // must still close it. Tab stays inside the card while it is open.
    document.addEventListener('keydown', function (e) {
      if (tour.at < 0) return;
      if (e.key === 'Escape' || e.key === 'Esc') { e.preventDefault(); tourClose(); return; }
      if (e.key !== 'Tab') return;
      var f = [].slice.call($('tour-card').querySelectorAll('input,button')).filter(function (x) { return !x.hidden; });
      var i = f.indexOf(document.activeElement);
      e.preventDefault();
      f[(i + (e.shiftKey ? f.length - 1 : 1)) % f.length].focus();
    });
    window.addEventListener('resize', tourLater);
    window.addEventListener('scroll', tourLater);
    var btn = $('tourbtn');
    btn.hidden = false;
    btn.addEventListener('click', tourOpen);

    var now = Date.now(), seen = Number(sGet(KEY_SEEN)) || 0;
    sSet(KEY_SEEN, String(now));
    return (!seen || now - seen > TOUR_GAP) && sGet(KEY_TOUR) !== 'off';
  }

  // ---------- wiring ----------
  function init() {
    loadPrefs();
    $('q').value = state.q;
    Array.prototype.forEach.call(document.querySelectorAll('.tab'), function (t) {
      t.addEventListener('click', function () {
        state.view = t.getAttribute('data-view');
        if (!tour.clicking) countView(state.view);
        savePrefs();
        rerender();
      });
    });
    $('q').addEventListener('input', function (e) {
      state.q = e.target.value;
      savePrefs();
      rerender();
    });
    $('t-1for1').addEventListener('click', function () { state.f1 = !state.f1; savePrefs(); rerender(); });
    $('t-free').addEventListener('click', function () { state.free = !state.free; savePrefs(); rerender(); });
    $('clear').addEventListener('click', function () {
      state.q = ''; state.cat = ''; state.area = ''; state.f1 = false; state.free = false;
      $('q').value = '';
      savePrefs();
      renderChips();
      rerender();
    });
    MONTHS.forEach(function (name, i) { $('bday-m').add(new Option(name, String(i + 1))); });
    var bd0 = bdayGet();
    fillDays(bd0 ? bd0.m : 0);
    if (bd0) { $('bday-m').value = String(bd0.m); $('bday-d').value = String(bd0.d); }
    $('bday-m').addEventListener('change', function () { fillDays(+$('bday-m').value); bdaySet(); rerender(); });
    $('bday-d').addEventListener('change', function () { bdaySet(); rerender(); });
    $('refresh').addEventListener('click', load);
    $('filter-btn').addEventListener('click', function () {
      var open = $('filters').hidden;
      $('filters').hidden = !open;
      $('filter-btn').setAttribute('aria-expanded', String(open));
    });
    $('health-btn').addEventListener('click', function () {
      healthOpen($('health-list').hidden);
    });
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) return;
      countOpen();
      countView(state.view);
      if (data) renderHeader();
    });
    countOpen();
    countView(state.view);
    renderControls();
    autoTour = tourInit();
    load();
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', function () {
        navigator.serviceWorker.register('./sw.js').catch(function () { /* ignore */ });
      });
    }
  }

  init();
})();
