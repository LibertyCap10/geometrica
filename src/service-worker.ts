// Minimal service worker for installability.
// We do not cache assets here yet; this is a simple pass-through SW.
//
// Later improvement: add caching for offline play + faster cold starts.

self.addEventListener('install', (event: ExtendableEvent) => {
  // Activate immediately on install
  // @ts-ignore
  self.skipWaiting?.();
});

self.addEventListener('activate', (event: ExtendableEvent) => {
  event.waitUntil(
    (async () => {
      // @ts-ignore
      await self.clients?.claim?.();
    })()
  );
});

self.addEventListener('fetch', (event: FetchEvent) => {
  // Pass-through network fetch. This satisfies "has a fetch handler" requirement.
  event.respondWith(fetch(event.request));
});
