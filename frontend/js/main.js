import { initMenu } from './menu.js';
import { initNotificationManager, showNotification } from './notifications.js';
import { initMap } from './map.js';

const menuAPI = initMenu();

const notifContainer = document.getElementById('notification-container');
initNotificationManager(notifContainer, {
    maxVisible: 3,
    autoHide: 5000
});

window.showNotification = showNotification;

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const map = await initMap({
            showNotification
        });
        console.log('[INIT] Map loaded:', map);
    } catch (e) {
        console.error('[INIT] Error loading map:', e);
        location.reload();
    }
});
