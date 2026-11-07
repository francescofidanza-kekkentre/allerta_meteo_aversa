// Strategia "network-first": il frontend viene sempre scaricato dalla rete
// (riconvalidando la cache HTTP di GitHub Pages) e la cache locale serve solo
// come ripiego offline. Non serve più cambiare CACHE_NAME a ogni modifica.
const CACHE_NAME = 'aversa-meteo-shell';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './manifest.json'
];
// Oltre questo tempo senza risposta si usa la copia in cache (rete lenta/assente).
const NETWORK_TIMEOUT_MS = 5000;

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(ASSETS_TO_CACHE.map((url) => new Request(url, { cache: 'no-cache' }))))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const oldKeys = (await caches.keys()).filter((key) => key !== CACHE_NAME);
    await Promise.all(oldKeys.map((key) => caches.delete(key)));
    await self.clients.claim();

    // Se c'era un service worker precedente (versione cache-first), le pagine
    // aperte potrebbero mostrare un frontend vecchio: ricaricale una volta.
    if (oldKeys.length > 0) {
      const windows = await self.clients.matchAll({ type: 'window' });
      windows.forEach((client) => client.navigate(client.url).catch(() => {}));
    }
  })());
});

function fetchWithTimeout(request) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('timeout')), NETWORK_TIMEOUT_MS);
    // Si usa l'URL: una Request di tipo "navigate" non accetta opzioni aggiuntive.
    fetch(request.url, { cache: 'no-cache', credentials: 'same-origin' }).then(
      (response) => { clearTimeout(timer); resolve(response); },
      (err) => { clearTimeout(timer); reject(err); }
    );
  });
}

async function networkFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  try {
    const response = await fetchWithTimeout(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await cache.match(request, { ignoreSearch: true })
      || (request.mode === 'navigate' && await cache.match('./index.html'));
    if (cached) return cached;
    throw err;
  }
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  // Dati sempre freschi, mai dalla cache
  if (request.url.includes('alert.json') || request.url.includes('open-meteo.com')) {
    event.respondWith(fetch(request, { cache: 'no-store' }));
    return;
  }

  // File dell'app (stesso dominio): prima la rete, cache solo offline
  if (new URL(request.url).origin === self.location.origin) {
    event.respondWith(networkFirst(request));
  }
  // Risorse esterne (CDN Tailwind/Chart.js, icone): gestite dal browser
});
