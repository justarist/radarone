# Radar ONE  
**Interactive real-time threat map**  
(Events in Russia and new regions collected from Telegram channels, processed by an LLM model, and delivered to subscribers via WebSocket and Telegram bot).

## 🗣️ README languages | Языки README:

- **[English](README.md)**
- **[Русский](README.ru.md)**

## 📚 Contents  

1. [Overview](#-overview)  
2. [Key Features](#-key-features)  
3. [Project Architecture](#-project-architecture)  
4. [Quick Start (Docker)](#-quick-start-docker)  
5. [Running Without Docker](#-running-without-docker)  
6. [Configuration and Environment Variables](#-configuration-and-environment-variables)  
7. [Database](#-database)  
8. [Backend (FastAPI)](#-backend-fastapi)  
9. [Frontend (Map & Notifications)](#-frontend)  
10. [Telegram Bot](#-telegram-bot)  
11. [Logs](#-logs)  
12. [Development & Contributing](#-development)  
13. [License](#-license)  
14. [Contacts](#-contacts)  

## 🌐 Overview  

Radar ONE collects messages from public Telegram channels reporting air, missile, and other threats.  
Messages are processed via an LLM model (OpenAI GPT o1‑mini **or** Ollama), extracting:

* **Region** – exact official name of a Russian federal subject.  
* **Threat Type** – `UAV` (drone attack), `AIR` (air threat), `ROCKET` (missile threat), `UB` (unmanned boat attack), or `ALL`.  
* **Status** – `HD` (high), `MD` (medium), or `AC` (all clear/no threat).

Extracted data is stored in PostgreSQL and delivered to subscribers via:

* **WebSocket** – real-time map updates and notifications.  
* **Telegram Bot** – push notifications and manual reporting of new threats.

## 🚀 Key Features  

| Feature | Implementation |
|---------|----------------|
| **Real-time updates** | `listener.py` scrapes Telegram channels every 10 sec, PostgreSQL notifies via `LISTEN/NOTIFY`. |
| **Automatic analysis** | LLM (`analyzer.py`) outputs `STATUS/REGION/TYPE`. Falls back to Ollama if OpenAI unavailable. |
| **Region subscriptions** | Telegram bot stores subscriptions in `subscriptions` table. |
| **Interactive map** | Frontend (MapLibre GL) displays region status, colors change with threat level. |
| **WebSocket API** | `snapshot` (full state) and `region_update` (single region updates). |
| **Telegram notifications** | Formatted HTML messages (`notifications.format_notification`). |
| **User management** | Admins (`ADMIN_USER_ID`) can ban/unban, broadcast messages, post reports. |
| **Logging** | `logger.py` logs to console and `logs/radarone.log` (daily rotation, 30 days). |
| **Docker Compose** | Single `docker-compose.yml` runs backend, frontend, Nginx, PostgreSQL, and Portainer. |

## 🏗️ Project Architecture  

```
+-------------------+        +------------------+        +--------------------+
| Telegram channels |  --->  |    listener.py   |  --->  |    analyzer.py     |
+-------------------+        +------------------+        +--------------------+
                                      |                            |
                                      v                            v
                             +------------------+        +---------+----------+
                             |    PostgreSQL    | <----> |   db.py (asyncpg)  |
                             +------------------+        +---------+----------+
                                      |                            |
                                      |                            |
                          +-----------+-----------+    +-----------+-----------+
                          |   FastAPI (backend)   |    |     Telegram Bot      |
                          +-----------+-----------+    +-----------+-----------+
                                      |                            |
                                      v                            v
                              +-------+--------+          +--------+--------+
                              |  WebSocket WS  |          |  Bot API (poll) |
                              +-------+--------+          +-----------------+
                                      |
                                      v
                            +---------+---------+
                            |  Frontend (NGINX) |
                            |  index.html + js  |
                            +-------------------+
```

* `listener.py` – scrapes public channels, sends text to `process_message`.  
* `analyzer.py` – LLM analysis, falls back to Ollama.  
* `db.py` – async PostgreSQL layer, creates tables on first run.  
* `main.py` – FastAPI server: HTTP API `/api/statuses`, WebSocket `/ws`, background tasks (listener, fallback poll, PG listen, bot in separate thread).  
* `bot.py` – Telegram bot, subscription/report/admin commands.  
* `frontend` – static files, connected to `/ws`, visualize map data.

## 📦 Quick Start (Docker)

> **Requirements:** Docker ≥ 20.10, Docker‑Compose ≥ 2.0 (built-in in Docker Desktop).

```
bash
# 1. Clone repository
git clone https://github.com/justarist/radarone.git
cd radarone

# 2. Copy example .env and fill in your values
cp .env.example .env   # if missing, create manually (see below)

# 3. Launch everything in containers
docker compose up -d   # or: docker-compose up -d

# 4. After successful start:
#    - Backend API   : http://localhost/api/statuses
#    - Map (frontend): http://localhost
#    - WebSocket endpoint (for testing) : ws://localhost/ws
```

Stop all:

```
bash
docker compose down
```

### Docker Container Structure  

| Service        | Image / Dockerfile | Ports | Purpose |
|----------------|------------------|-------|---------|
| `backend`      | `python:3.13-slim` (see `backend/Dockerfile`) | 8000 (internal) | FastAPI + listener + bot thread |
| `frontend`     | `nginx:alpine` (see `frontend/Dockerfile`) | 80 (internal) | Static files (HTML, CSS, JS) |
| `nginx-proxy`  | `nginx:alpine` | 80 / 443 → host | Reverse proxy, TLS (Let's Encrypt) |
| `postgres`     | `postgres:16` | 5432 | Threat message storage |
| `portainer`    | `portainer/portainer-ce` | 9000 | Docker management UI |

## 🛠️ Running Without Docker (Development)

```
bash
# 1. Install Python (>=3.13) and PostgreSQL
# 2. Clone repo
git clone https://github.com/justarist/radarone.git
cd radarone

# 3. Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Create .env (see below)

# 5. Start PostgreSQL (can be Docker or local)
#    Ensure database `attacks` is available.

# 6. Start backend
uvicorn main:app --host 0.0.0.0 --port 8000

# 7. Open index.html in browser (or simple HTTP server):
cd frontend
python -m http.server 8080   # map available at http://localhost:8080
```

## 🔧 Configuration & Environment Variables  

### Example `.env`

```
dotenv
# ------------------ Server -------------------
HOST=0.0.0.0
PORT=8000
POLL_FALLBACK_SEC=15  # fallback poll interval, sec

# ------------------ DB -----------------------
DB_USER=postgres
DB_PASSWORD=760942
DB_NAME=attacks
DB_HOST=postgres  # container name in docker-compose, otherwise localhost
DB_PORT=5432

# ------------------ Telegram -----------------
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11  # your bot token
ADMIN_USER_ID=111111111,222222222  # admin Telegram IDs

# ------------------ LLM ----------------------
OPENAI_API_KEY=sk-****************************************  # if using OpenAI
OLLAMA_API_KEY=YOUR_OLLAMA_API_KEY  # if using Ollama
OLLAMA_MODEL=gemma:2b  # example, can be any available
```

#### About Variables  

| Variable | Description |
|----------|------------|
| `HOST`, `PORT` | IP/port to run FastAPI. |
| `POLL_FALLBACK_SEC` | Fallback polling interval if `LISTEN` not available. |
| `DB_*` | PostgreSQL connection parameters. |
| `BOT_TOKEN` | Telegram bot token (for notifications & admin commands). |
| `ADMIN_USER_ID` | Comma-separated list of admin Telegram IDs. |
| `OPENAI_API_KEY` | OpenAI key (if using GPT‑o1‑mini). |
| `OLLAMA_API_KEY` | Ollama cloud access token. |
| `OLLAMA_MODEL` | Ollama model name, e.g., `gemma:2b` or `llama3`. |

> **Note:** Without Docker, `DB_HOST` is usually `localhost`. In Docker‑compose leave `postgres` as it is the service name in `radarnet` network.

### Regional Data (`config.py`)

* `region_names` – official names of supported regions (including `"Россия"` for nationwide threats). Restart backend after changes.  
* `telegram_channels` – public Telegram channels to scrape. Add new channels by appending name (without `@`) to this array.

## 📂 Database  

Tables are created automatically on first connection (`db._init_schema`).  

| Table | Fields | Description |
|-------|-------|------------|
| `attacks` | `id` (PK), `region`, `attack_type`, `status`, `source`, `timestamp` | Threat events. |
| `subscriptions` | `id` (PK), `user_id`, `region`, `is_banned` (bool) | User subscriptions & ban status. |
| **Trigger** `attack_insert_trigger` | | On `INSERT` into `attacks`, calls `pg_notify('attack_updates', row_to_json(NEW)::text)`. |

**Indexes**: `idx_region_attack_type` speeds up queries for latest region/type statuses.

## ⚡ Backend (FastAPI)

### HTTP API  

| Method | Path | Description | Example Response |
|--------|------|------------|----------------|
| `GET` | `/api/statuses` | Returns current statuses as `{region: {attack_type: status}}`. | ```json { "Moscow Oblast": { "UAV": "HD", "AIR": "MD" }, "Crimea": { "UB": "AC" } }``` |
| `GET` | `/` | (implicit) FastAPI docs page. |
| **WebSocket** | `/ws` | On connect, client receives **snapshot** (full current state). Server sends: <br> *`type: "region_update"`* – region update <br> *`type: "snapshot"`* – full snapshot | ```json { "type": "region_update", "data": { "region": "Crimea", "statuses": { "UAV": "HD", "AIR": "MD", "ROCKET": "AC" } } }``` |

### Running (without Docker)

```
bash
uvicorn main:app --host $HOST --port $PORT
```

> On start, the service runs:  
> * `listener.listener_loop` – scrape Telegram channels (every 10 sec by default).  
> * `listener.poll_and_broadcast_loop` – fallback poll if `LISTEN` unavailable.  
> * `listener.pg_listen_and_forward` – subscribe to `PG_NOTIFY_CHANNEL`.  
> * `bot.main()` – Telegram bot in separate thread.

## 🎨 Frontend (Map)

* **HTML** – `frontend/index.html`.  
* **JS modules** – `js/main.js`, `js/map.js`, `js/notifications.js`, `js/ws.js`, `js/utils.js`, `js/menu.js`.  
* **CSS** – `css/styles.css`.  

### How It Works

1. `main.js` initializes `maplibre-gl` map and WebSocket connection to `ws(s)://HOST/ws`.  
2. On first connect, server sends **snapshot** with all region statuses.  
3. On `region_update`, `updateRegionStatus` updates:  
   * `REGION_STATUS` object.  
   * Polygon color on map.  
   * Calls `showNotification` (popup).

### Notification Text (frontend)

HTML message formatting done via `utils.js`:  
* `formatNotification` – converts status/type code to human-readable Russian text.  
* `getColorByStatus` – color scale: `HD` → red, `MD` → yellow, `AC` → green.

### Customization

* Edit `css/styles.css` to change notification styles.  
* Add new threat types in `utils.formatNotification` and `utils.getColorByStatus`.

## 📱 Telegram Bot

Implemented in `bot.py` using **python-telegram-bot** (v20+).

### Main Commands

| Command | Parameters | Description |
|---------|-----------|------------|
| `/start` | – | Welcome message & instructions. |
| `/help` | – | List of all commands. |
| `/status <region>` | Region | Last 5 events in the region. |
| `/subscribe <region>` | Region / `all` | Subscribe to notifications. |
| `/unsubscribe <region>` | Region / `all` | Unsubscribe. |
| `/subscriptions` | – | Show current subscriptions. |
| `/report` | – | Submit threat report (moderated). |
| `/channels` | – | List Telegram channels scraped. |
| `/about` | – | Project info. |
| **Admin** `/ban <user_id> <reason>` | – | Ban user (disable `/report`). |
| **Admin** `/unban <user_id> <reason>` | – | Unban user. |
| **Admin** `/is_banned <user_id>` | – | Check ban status. |
| **Admin** `/admin_report <message>;<comment>` | – | Send report without moderation. |
| **Admin** `/admin_message <text>` | – | Broadcast to all users. |

> **Note:** To become admin, add your Telegram ID to `ADMIN_USER_ID`.

### `/report` Flow

1. User sends free-form message.  
2. Bot forwards to each admin with `✅ Approve / ❌ Reject`.  
3. If approved, message enters `process_message` pipeline (same as Telegram channels).

## 📁 Logs  

`logger.py` uses standard `logging`:

* **Console** – INFO level.  
* **Files** – `logs/radarone.log`, daily rotation, 30 days retention.  
* **EmojiStripFilter** – removes emojis from logs.

Change log level in `logger.py` via `logger.setLevel(logging.INFO)`.

## 🛠️ Development  

### Branches

* `main` – stable production.  
* `feature/*` – new features, submit Pull Requests.

### Adding Region / Threat Type

1. **Region** – add to `config.region_names`.  
2. **Territorial mapping** – optionally update `map.js` (`nameMap`).  
3. **Threat type** – update `utils.formatNotification`, `utils.getColorByStatus`, optionally `allowedUB` in `map.js`.

### Adding Telegram Channel

```
python
# config.py
telegram_channels = [
    "radarrussiia",
    "bidengoy",
    "RDFradar",
    "lpr1_Kherson_alarm",
    "my_new_channel",  # ← add here
]
```

Restart `backend` – new channels are scraped automatically.

## 📜 License  

MIT License. Full text in [LICENSE](LICENSE).

## ☎️ Contacts

* **Telegram channel** – https://t.me/radaroneteam  
* **Telegram bot** – https://t.me/radaronebot  
* **GitHub** – https://github.com/justarist/radarone  
* **Donate** – https://radarone.online/donate

## ✍️ Authors

* Main author & developer (Backend + Frontend + nginx + Docker) – [JustArist](https://github.com/justarist)  
* Co-author, Backend developer (listener.py etc.) – [perlch](https://github.com/perlch)

