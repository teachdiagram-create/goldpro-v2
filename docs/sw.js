// نسخه جدید — نسخه رو عوض کردیم تا cache قدیمی پاک بشه
const CACHE_NAME = 'goldpro-v3-' + Date.now();

self.addEventListener('install', event => {
  console.log('[SW] Installing v3...');
  // فوراً فعال شو
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  console.log('[SW] Activating v3...');
  event.waitUntil(
    // همه cache های قدیمی رو پاک کن
    caches.keys().then(keys =>
      Promise.all(keys.map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Gist API → مستقیم از شبکه
  if (url.hostname === 'api.github.com' || url.hostname === 'gist.githubusercontent.com') {
    event.respondWith(fetch(event.request));
    return;
  }

  // HTML و manifest → اول از شبکه (network-first)
  // اگه شبکه نبود → از cache
  if (url.pathname.endsWith('.html') || 
      url.pathname.endsWith('/') || 
      url.pathname.endsWith('manifest.json')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // بقیه فایل‌ها (CDN و ...) → اول از cache
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});