import { getIconByType, formatNotification, getColorByStatus } from './utils.js';

class NotificationManager {
    constructor(container, { maxVisible = 3, autoHide = 5000 } = {}) {
        if (!container) {
            throw new Error('[NotificationManager] container element is required');
        }
        this.container  = container;
        this.maxVisible = maxVisible;
        this.autoHide   = autoHide;
        this.queue      = [];
        this.active     = [];
    }

    show(regionText, attackText, type) {
        this.queue.push({ regionText, attackText, type });
        this._processQueue();
    }

    _processQueue() {
        if (this.active.length >= this.maxVisible || this.queue.length === 0) return;

        const { regionText, attackText, type } = this.queue.shift();
        const note = this._createNotification(regionText, attackText, type);
        this.active.push(note);
        this.container.appendChild(note.el);
        note.el.getBoundingClientRect();
        requestAnimationFrame(() => note.el.classList.add('show'));

        this._processQueue();
    }

    _createNotification(regionText, attackText, rawType) {
        const type = ['AC', 'MD', 'HD'].includes(rawType) ? rawType : 'default';
        const el   = document.createElement('div');
        el.className = `notification ${type}`;

        el.innerHTML = `
            <div class="notification-header">
                <span class="notification-title material-symbols-outlined icon-md">
                    ${getIconByType(type)}
                </span>
                <div class="notification-subtitle">Тип угрозы</div>
                <div class="notification-close">
                    <span class="material-symbols-outlined icon-sm">close</span>
                </div>
            </div>
            <div class="notification-text">${attackText || 'Неизвестно'}</div>
            <div class="notification-subtitle">Регион</div>
            <div class="notification-text">${regionText || 'Неизвестно'}</div>
            <div class="notification-subtitle">Статус</div>
            <div class="notification-text" style="color: ${getColorByStatus(type)};"><b>${formatNotification(type) || 'Не задан'}</b></div>
            <div class="notification-progress">
                <div class="notification-progress-bar"></div>
            </div>
        `;

        const progressBar = el.querySelector('.notification-progress-bar');
        const closeBtn    = el.querySelector('.notification-close');

        let remaining = this.autoHide;
        let startTime = performance.now();
        let paused    = false;
        let rafId;

        const tick = now => {
            if (paused) {
                startTime = now;
                rafId = requestAnimationFrame(tick);
                return;
            }
            const delta = now - startTime;
            startTime = now;
            remaining -= delta;

            const progress = Math.max(remaining / this.autoHide, 0);
            progressBar.style.transform = `scaleX(${progress})`;

            if (remaining <= 0) {
                hide();
            } else {
                rafId = requestAnimationFrame(tick);
            }
        };

        const hide = () => {
            cancelAnimationFrame(rafId);
            el.classList.add('hide');
            el.classList.remove('show');
            el.addEventListener('transitionend', () => {
                el.remove();
                this.active = this.active.filter(item => item !== api);
                this._processQueue();
            }, { once: true });
        };

        el.addEventListener('mouseenter', () => (paused = true));
        el.addEventListener('mouseleave', () => (paused = false));
        closeBtn.addEventListener('click', hide);

        rafId = requestAnimationFrame(tick);

        const api = { el, hide };
        return api;
    }
}

let _manager = null;

export function initNotificationManager(container, options) {
    _manager = new NotificationManager(container, options);
}

export function showNotification(region, attack, type) {
    if (!_manager) {
        console.warn('[notifications] manager not initialized – ignoring showNotification');
        return;
    }
    _manager.show(region, attack, type);
}
