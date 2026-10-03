(function () {
  'use strict';

  var TZ = 'Asia/Singapore';
  var STALE_MS = 12 * 3600 * 1000;
  var KEY_PREFS = 'lobang:prefs';
  var KEY_SAVED = 'lobang:saved';
  var VIEWS = ['hot', 'ending', 'new', 'saved'];

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
    saved: ['Nothing saved yet', 'Tap Save on a deal and it will show up here.']
  };

  var state = { view: 'hot', q: '', cat: '', f1: false, free: false };
  var saved = {};
  var data = null;
  var loading = false;
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
    sSet(KEY_PREFS, JSON.stringify({ view: state.view, q: state.q, cat: state.cat, f1: state.f1, free: state.free }));
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

  function validity(d) {
    if (!d.valid_until) return { text: 'Validity not stated', cls: 'unknown' };
    var left = daysLeft(d.valid_until);
    if (left === 0 || hasTag(d, 'ends-today')) return { text: 'Ends today', cls: 'today' };
    var s = 'Till ' + fmtDate(d.valid_until);
    if (left != null && left > 0) s += ' · ' + left + (left === 1 ? ' day left' : ' days left');
    return { text: s, cls: '' };
  }

  // ---------- filtering / views ----------
  function matches(d) {
    if (state.cat && d.category !== state.cat) return false;
    if (state.f1 && !hasTag(d, '1-for-1')) return false;
    if (state.free && !hasTag(d, 'free')) return false;
    var q = state.q.trim().toLowerCase();
    if (q) {
      var hay = (merchantsOf(d).join(' ') + ' ' + (d.title || '') + ' ' + (d.summary || '')).toLowerCase();
      if (hay.indexOf(q) < 0) return false;
    }
    return true;
  }

  function selectDeals() {
    var all = (data && data.deals) || [];
    var list = all.filter(matches);
    if (state.view === 'ending') {
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
    var merch = merchantsOf(d);
    c.appendChild(el('div', 'kind', d.kind === 'opening' ? 'New opening' : 'Promo'));
    c.appendChild(el('h2', 'merch', merch.length ? merch.join(' + ') : 'Unknown merchant'));
    if (d.title) c.appendChild(el('p', 'title', d.title));

    var bs = badgesFor(d);
    if (bs.length) {
      var ul = el('ul', 'badges');
      bs.forEach(function (b) { ul.appendChild(el('li', 'badge ' + b[1], b[0])); });
      c.appendChild(ul);
    }

    var v = validity(d);
    c.appendChild(el('p', 'valid ' + v.cls, v.text));

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
    var shownN = links.length;
    var total = typeof d.publishers === 'number' ? d.publishers : shownN;
    if (shownN) {
      var src = el('p', 'sources');
      src.appendChild(el('span', null, 'Source:'));
      links.forEach(function (l) {
        var a = el('a', null, l.pub || new URL(l.url).hostname);
        a.href = l.url;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        if (l.title) a.title = l.title;
        src.appendChild(a);
      });
      if (total > shownN) src.appendChild(el('span', 'more', '+' + (total - shownN) + ' more sources'));
      c.appendChild(src);
    }

    var act = el('div', 'actions');
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
    return c;
  }

  function share(d, url) {
    var link = url || location.href;
    var title = merchantsOf(d).join(' + ') + ': ' + (d.title || 'deal');
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

  function renderHeader() {
    var fresh = $('fresh-text'), stale = $('stale');
    var h = $('health');
    if (!data) { h.hidden = true; stale.hidden = true; return; }
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
      $('health-sum').textContent = hl.ok + '/' + hl.total + ' sources';
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
    } else {
      h.hidden = true;
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
        render();
      });
      box.appendChild(b);
    });
  }

  function renderControls() {
    Array.prototype.forEach.call(document.querySelectorAll('.tab'), function (t) {
      t.setAttribute('aria-selected', String(t.getAttribute('data-view') === state.view));
    });
    $('t-1for1').setAttribute('aria-pressed', String(state.f1));
    $('t-free').setAttribute('aria-pressed', String(state.free));
    $('clear').hidden = !(state.q || state.cat || state.f1 || state.free);
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
    deals.forEach(function (d) { frag.appendChild(card(d)); });
    list.appendChild(frag);
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
        $('health').hidden = true;
        showState('err', 'Could not load deals',
          'The deals file did not load (' + (err && err.message ? err.message : 'network error') + '). This is a loading problem, not an empty list.', true);
      }
    }).then(function () {
      loading = false;
      btn.disabled = false;
    });
  }

  // ---------- wiring ----------
  function init() {
    loadPrefs();
    $('q').value = state.q;
    Array.prototype.forEach.call(document.querySelectorAll('.tab'), function (t) {
      t.addEventListener('click', function () {
        state.view = t.getAttribute('data-view');
        savePrefs();
        render();
      });
    });
    $('q').addEventListener('input', function (e) {
      state.q = e.target.value;
      savePrefs();
      render();
    });
    $('t-1for1').addEventListener('click', function () { state.f1 = !state.f1; savePrefs(); render(); });
    $('t-free').addEventListener('click', function () { state.free = !state.free; savePrefs(); render(); });
    $('clear').addEventListener('click', function () {
      state.q = ''; state.cat = ''; state.f1 = false; state.free = false;
      $('q').value = '';
      savePrefs();
      renderChips();
      render();
    });
    $('refresh').addEventListener('click', load);
    document.addEventListener('visibilitychange', function () { if (!document.hidden && data) renderHeader(); });
    renderControls();
    load();
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', function () {
        navigator.serviceWorker.register('./sw.js').catch(function () { /* ignore */ });
      });
    }
  }

  init();
})();
