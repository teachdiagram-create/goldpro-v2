const CACHE_NAME = 'goldpro-auto-v1';

// ✅ هر بار که SW نصب می‌شه، فوراً فعال شو
self.addEventListener('install', event => {
  console.log('[SW] Installing...');
  self.skipWaiting();
});

// ✅ هر بار که SW فعال می‌شه، همه تب‌ها رو کنترل کن
// و Cache های قدیمی رو پاک کن
self.addEventListener('activate', event => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Gist API → مستقیم از شبکه (همیشه تازه)
  if (url.hostname === 'api.github.com' || url.hostname === 'gist.githubusercontent.com') {
    return; // بی‌خیال، مرورگر خودش مدیریت کنه
  }

  // فقط درخواست‌های GET رو کش کن
  if (event.request.method !== 'GET') return;

  // HTML، manifest → Network First با no-cache
  if (url.pathname.endsWith('.html') ||
      url.pathname.endsWith('/') ||
      url.pathname.endsWith('manifest.json') ||
      url.pathname.endsWith('.js')) {
    event.respondWith(
      fetch(event.request, { cache: 'no-store' })
        .then(response => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // بقیه (آیکون، فونت، Chart.js) → Cache First
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        return response;
      });
    })
  );
});