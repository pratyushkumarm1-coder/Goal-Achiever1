const CACHE_NAME = 'goalachiever-v1';
const STATIC_ASSETS = [
  '/',
  '/dashboard/',
  '/static/css/style.css',
  '/static/js/main.js',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap',
];

// ── Install: cache static assets ─────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.log('SW: Some assets failed to cache:', err);
      });
    })
  );
  self.skipWaiting();
});

// ── Activate: clean old caches ──────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// ── Fetch: network-first, fallback to cache ─────────────────
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});

// ── Background Reminder Alarm ───────────────────────────────
// The SW has its own timer — runs even when all tabs are closed.
let reminderInterval = null;

function startReminderCheck() {
  if (reminderInterval) return;
  reminderInterval = setInterval(() => {
    self.clients.matchAll().then((clients) => {
      if (clients.length === 0) return; // no open tabs — don't check
      clients[0].postMessage({ type: 'CHECK_REMINDERS' });
    });
  }, 20000);
}

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'START_REMINDERS') {
    startReminderCheck();
  }
  if (event.data && event.data.type === 'STOP_REMINDERS') {
    clearInterval(reminderInterval);
    reminderInterval = null;
  }
  if (event.data && event.data.type === 'FIRE_ALARM') {
    const { habitName, habitId } = event.data;
    self.registration.showNotification('GoalAchiever Reminder', {
      body: `Time to complete: ${habitName}!`,
      icon: '/static/favicon.png',
      badge: '/static/favicon.png',
      tag: `habit-${habitId}`,
      renotify: true,
      requireInteraction: true,
      actions: [
        { action: 'open', title: 'Open GoalAchiever' },
      ],
    });
  }
});

// ── Notification Click ──────────────────────────────────────
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((clients) => {
      for (const client of clients) {
        if (client.url.includes('/dashboard/') && 'focus' in client) {
          return client.focus();
        }
      }
      return self.clients.openWindow('/dashboard/');
    })
  );
});

// ── Push notifications (future: server-sent reminders) ─────
self.addEventListener('push', (event) => {
  if (!event.data) return;
  const data = event.data.json();
  event.waitUntil(
    self.registration.showNotification(data.title || 'GoalAchiever', {
      body: data.body || 'Check your habits!',
      icon: '/static/favicon.png',
      badge: '/static/favicon.png',
      data: data,
    })
  );
});
