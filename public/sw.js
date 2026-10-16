const CACHE = 'lobang-v12';
const ASSETS = ['./', './app.css', './app.js', './manifest.webmanifest', './icon-192.png',
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
  if (req.mode === 'navigate' || url.pathname.endsWith('/deals.json')) {
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
