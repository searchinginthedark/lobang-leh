const CACHE = 'lobang-v16';
// embed/ (the search model: vocab.txt + t/<k>.bin shards) is NOT precached: ~16 MB in all, of
// which a query needs a few shards. They are cached as they are fetched (cache-first below) and
// never change unless the model does, which needs a CACHE bump here.
const ASSETS = ['./', './app.css', './app.js', './embed.js', './manifest.webmanifest', './icon-192.png',
  './fonts/PlusJakartaSans-latin.woff2', './fonts/BagelFatOne-latin.woff2',
  './stickers/restaurant.png', './stickers/bakery-dessert.png', './stickers/buffet.png',
  './stickers/hawker.png', './stickers/fast-food.png', './stickers/delivery.png',
  './stickers/coffee.png', './stickers/cafe.png', './stickers/bubble-tea.png',
  './stickers/bar-drinks.png', './stickers/grocery.png', './stickers/other.png',
  './stickers/birthday.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => Promise.all(ASSETS.map((a) => c.add(a).catch(() => {}))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function networkFirst(req) {
  return fetch(req).then((res) => {
    if (res && res.ok) {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
    }
    return res;
  }).catch(() => caches.match(req).then((hit) => hit || Promise.reject(new Error('offline'))));
}

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // The digest's functions are never cached: the cache-first branch below would pin any GET forever.
  if (url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;
  // The three files each collect rewrites: always the network's copy, the cache only offline.
  if (req.mode === 'navigate' || /\/(deals|details|vectors)\.json$/.test(url.pathname)) {
    e.respondWith(networkFirst(req));
    return;
  }
  e.respondWith(
    caches.match(req).then((hit) => hit || fetch(req).then((res) => {
      if (res && res.ok) {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
      }
      return res;
    }))
  );
});

// Morning digest (api/digest.js): one notification a day, the 3 best new deals.
self.addEventListener('push', (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (err) { d = { body: e.data ? e.data.text() : '' }; }
  e.waitUntil(self.registration.showNotification(d.title || 'New lobangs today', {
    body: d.body || '',
    icon: './icon-192.png',
    badge: './icon-192.png',
    // One tag: a re-sent digest replaces the day's notification instead of stacking.
    tag: d.tag || 'lobang-digest',
    data: { url: d.url || './' }
  }));
});

self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  e.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      for (const c of list) {
        if (c.url.indexOf(self.registration.scope) === 0 && 'focus' in c) return c.focus();
      }
      return self.clients.openWindow((e.notification.data && e.notification.data.url) || './');
    })
  );
});
