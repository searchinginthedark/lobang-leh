const CACHE = 'lobang-v14';
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
  if (url.origin !== self.location.origin) return;
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
