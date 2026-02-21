// Project Titan - Service Worker (Push Notifications)

self.addEventListener('push', (event) => {
    let data = { title: 'Project Titan', body: '새로운 알림이 있습니다.' };
    try {
        data = event.data.json();
    } catch (e) {
        data.body = event.data ? event.data.text() : data.body;
    }

    const options = {
        body: data.body || '',
        icon: data.icon || 'icons/icon-192.png',
        badge: 'icons/icon-192.png',
        tag: data.tag || 'titan-alert',
        data: { url: data.url || 'index.html' },
        requireInteraction: data.requireInteraction || false,
        actions: data.actions || []
    };

    event.waitUntil(
        self.registration.showNotification(data.title || 'Project Titan', options)
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const url = event.notification.data?.url || 'index.html';
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
            for (const client of windowClients) {
                if (client.url.includes('stock-recommendation_2.0') && 'focus' in client) {
                    return client.focus();
                }
            }
            return clients.openWindow(url);
        })
    );
});

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));
