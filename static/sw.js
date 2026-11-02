// Sindhi Digital Classroom (SDC) Service Worker
// Authored under agency-frontend-developer following ECC progressive-web-apps guidelines.

const CACHE_NAME = 'sdc-app-shell-v6';
const ASSETS_TO_CACHE = [
  '/',
  '/app',
  '/app/learn',
  '/app/progress',
  '/app/tools',
  '/static/app.html',
  '/static/index.html',
  '/static/classroom.html',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/js/db.js',
  '/static/js/player.js',
  '/static/js/quiz.js',
  '/static/js/tutor.js',
  '/static/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SDC ServiceWorker] Caching app shell assets');
      return cache.addAll(ASSETS_TO_CACHE).catch(err => {
        console.warn('[SDC ServiceWorker] Pre-cache non-fatal warning:', err);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[SDC ServiceWorker] Removing old cache', key);
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // For static assets: Network first so updates are immediately visible, cache fallback for offline
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      fetch(event.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const resClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, resClone));
        }
        return networkResponse;
      }).catch(() => {
        return caches.match(event.request);
      })
    );
    return;
  }

  // For API calls: Network first; on network failure return 503 with offline indicator so client falls back to local pack search
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request).catch(() => {
        return new Response(
          JSON.stringify({ offline: true, message: "Offline mode: network unreachable" }),
          { status: 503, headers: { 'Content-Type': 'application/json' } }
        );
      })
    );
    return;
  }

  // HTML navigation: Stale-while-revalidate
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
