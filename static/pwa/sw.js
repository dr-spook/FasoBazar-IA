// static/pwa/sw.js
// FasoBazar IA — Service Worker PWA
// Stratégie : Cache First pour les assets statiques, Network First pour les API

const CACHE_NAME = 'fasobazar-v1';
const CACHE_NAME_DYNAMIC = 'fasobazar-dynamic-v1';

// Assets à mettre en cache immédiatement (app shell)
const STATIC_ASSETS = [
  '/',
  '/app/',
  '/journal/',
  '/score/',
  '/static/pwa/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/api/health/',
  // Bootstrap et icons via CDN — on les cache au premier chargement
];

// ── Installation ───────────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      // Cache silencieux — on ne bloque pas sur les erreurs CDN
      return cache.addAll(STATIC_ASSETS).catch(() => {});
    })
  );
  self.skipWaiting();
});

// ── Activation — nettoyer les anciens caches ───────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== CACHE_NAME && k !== CACHE_NAME_DYNAMIC)
          .map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// ── Fetch — stratégie hybride ──────────────────────────────
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // API calls → Network First (données temps réel)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(event.request));
    return;
  }

  // POST → toujours réseau (transactions, uploads audio)
  if (event.request.method !== 'GET') {
    event.respondWith(fetch(event.request).catch(() =>
      new Response(JSON.stringify({
        success: false,
        error: { code: 'OFFLINE', message: 'Pas de connexion. Active le Mode Oz.' }
      }), { headers: { 'Content-Type': 'application/json' } })
    ));
    return;
  }

  // Assets statiques → Cache First
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  // CDN (Bootstrap, Google Fonts) → Cache First
  if (url.origin !== self.location.origin) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  // Pages HTML → Network First avec fallback cache
  event.respondWith(networkFirst(event.request));
});

// ── Stratégies ─────────────────────────────────────────────
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME_DYNAMIC);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('', { status: 503 });
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME_DYNAMIC);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    return cached || new Response('Hors ligne', { status: 503 });
  }
}

// ── Notification push (pour usage futur) ──────────────────
self.addEventListener('push', event => {
  const data = event.data?.json() || {};
  self.registration.showNotification(data.title || 'FasoBazar IA', {
    body:    data.body || 'Nouvelle notification',
    icon:    '/static/icons/icon-192x192.png',
    badge:   '/static/icons/icon-72x72.png',
    vibrate: [100, 50, 100],
    data:    { url: data.url || '/app/' },
  });
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data.url));
});