export class ReconnectingWebSocket {
    constructor(url, options = {}) {
    this.url = url;
    this.baseDelay   = options.baseDelay ?? 1000;
    this.maxDelay    = options.maxDelay ?? 30000;
    this.maxAttempts = options.maxAttempts ?? 0;
    this.debug       = options.debug ?? false;

    this.onopen    = null;
    this.onmessage = null;
    this.onerror   = null;
    this.onclose   = null;

    this._ws          = null;
    this._attempts    = 0;
    this._timer       = null;
    this._manualClose = false;

    this._connect();
    }

    _connect() {
    if (this.debug) console.info('[RWS] Connecting to WS', this.url);
    this._ws = new WebSocket(this.url);

    this._ws.onopen = (ev) => {
        if (this.debug) console.info('[RWS] Connected');
        this._attempts = 0;
        this._clearTimer();
        if (typeof this.onopen === 'function') this.onopen(ev);
    };

    this._ws.onmessage = (ev) => {
        if (typeof this.onmessage === 'function') this.onmessage(ev);
    };

    this._ws.onerror = (ev) => {
        if (typeof this.onerror === 'function') this.onerror(ev);
    };

    this._ws.onclose = (ev) => {
        if (typeof this.onclose === 'function') this.onclose(ev);
        if (this._manualClose) {
        if (this.debug) console.info('[RWS] Manual close – stopped reconnecting');
        return;
        }
        this._scheduleReconnect();
    };
    }

    _scheduleReconnect() {
    if (this._timer) return;

    if (this.maxAttempts && this._attempts >= this.maxAttempts) {
        if (this.debug) console.error('[RWS] Reconnect limit reached – stopped reconnecting');
        return;
    }

    const delay = Math.min(
        this.baseDelay * 2 ** this._attempts,
        this.maxDelay
    );

    if (this.debug) console.warn(`[RWS] Reconnect #${this._attempts + 1} in ${delay} ms`);
    this._timer = setTimeout(() => {
        this._attempts += 1;
        this._timer = null;
        this._connect();
    }, delay);
    }

    _clearTimer() {
    if (this._timer) {
        clearTimeout(this._timer);
        this._timer = null;
    }
    }

    send(data) {
    if (this._ws && this._ws.readyState === WebSocket.OPEN) {
        this._ws.send(data);
    } else {
        console.warn('[RWS] Attempt to send while socket not open – dropping');
    }
    }

    close(code = 1000, reason) {
    this._manualClose = true;
    this._clearTimer();
    if (this._ws) this._ws.close(code, reason);
    }

    get readyState() {
    return this._ws ? this._ws.readyState : WebSocket.CLOSED;
    }
}