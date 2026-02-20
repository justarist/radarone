# Radar ONE  
Operational Threat Monitoring Information System

## README Languages / Языки README

README is available in these languages:
- [English / Английский](README.md)
- [Russian / Русский](README.ru.md)

## Contents

1. [System Overview](#1-system-overview)
2. [System Architecture](#2-system-architecture)
3. [System Operation](#3-system-operation)
   - [3.1 Message Retrieval](#31-message-retrieval)
   - [3.2 Pre-filtering](#32-pre-filtering)
   - [3.3 Message Classification](#33-message-classification)
   - [3.4 Processing Analysis Results](#34-processing-analysis-results)
   - [3.5 Data Persistence](#35-data-persistence)
   - [3.6 Telegram Bot](#36-telegram-bot)
   - [3.7 HTTP API](#37-http-api)
   - [3.8 WebSocket](#38-websocket)
   - [3.9 Frontend](#39-frontend)
4. [Project Structure](#4-project-structure)
5. [Change Management](#5-change-management)
   - [5.1 General Rules](#51-general-rules)
   - [5.2 Modifying Classification Logic](#52-modifying-classification-logic)
   - [5.3 Adding a New Region](#53-adding-a-new-region)
   - [5.4 Adding a New Threat Type](#54-adding-a-new-threat-type)
   - [5.5 Modifying the Telegram Bot](#55-modifying-the-telegram-bot)
   - [5.6 Testing Procedure](#56-testing-procedure)
6. [Commit Requirements](#6-commit-requirements)
7. [Pre-Deployment Checklist](#7-pre-deployment-checklist)
8. [Logging](#8-logging)
9. [Additional Information](#9-additional-information)
10. [Licensing](#10-licensing)

## 1. System Overview

Radar ONE is a distributed information system designed for automated monitoring of Telegram channels, classification of threat-related messages, and delivery of aggregated information to users via:

- Telegram bot: https://t.me/radaronebot  
- Interactive online map: https://radarone.online  
- HTTP API  
- WebSocket connection  

The system is implemented in Python using an asynchronous architecture and a PostgreSQL database.

## 2. System Architecture

The system consists of the following logical components:

```
+-------------------+
| Telegram Channels |
+---------+---------+
          |
          V
+---------+---------+         +-------------------+
|   listener.py     | <-----> | analyzer.py (LLM) |
+---------+---------+         +-------------------+
          |
          |        +--------------+
          +------> | Telegram Bot |
          |        +--------------+
          |
          |        +---------------------+
          +------> | db.py (PostgreSQL)  |
                   +----------+----------+
                              |
                              V
                   +----------+----------+
                   |   FastAPI Backend   |
                   +----------+----------+
                              |
                              |        +----------------------------+
                              +------> | HTTP API (/api/statuses)   |
                              |        +----------------------------+
                              |
                              |        +------------------+
                              +------> | WebSocket (/ws)  |
                                       +--------+---------+
                                                |
                                                V
                                       +--------+---------+
                                       |    Online Map    |
                                       +------------------+
```

All backend components operate within a single asyncio event loop.

## 3. System Operation

### 3.1 Message Retrieval

The `listener.py` module performs:

- asynchronous polling of Telegram channels defined in `TELEGRAM_CHANNELS`;
- fetching channel HTML pages using aiohttp;
- extracting the latest message via BeautifulSoup;
- deduplication of messages;
- forwarding new messages to the `process_message()` handler.

The default polling interval is 10 seconds.

### 3.2 Pre-filtering

The `preprocess_message()` function:

- filters messages based on a list of banned words (`BANWORDS`);
- excludes irrelevant messages before passing them to the analysis module.

### 3.3 Message Classification

Classification is performed by the `analyze_message()` function in `analyzer.py` using an LLM:

- OpenAI (if `OPENAI_API_KEY` is defined);
- Ollama (if `OLLAMA_MODEL` and `OLLAMA_API_KEY` are defined and OpenAI fails).

The model returns results in the following format:

```
(threat_level)/(region)/(threat_type)
```

If multiple events are present, the result contains multiple entries separated by commas:

```
(threat_level_1)/(region_1)/(threat_type_1),(threat_level_2)/(region_2)/(threat_type_2)
```

### 3.4 Processing Analysis Results

The `process_message()` function:

- splits the LLM result into individual components;
- normalizes the region using `normalize_region()`;
- validates the threat type;
- generates a list of target updates via `expand_targets()`;
- calls `handle_attack_update()` for each detected event.

### 3.5 Data Persistence

The `db.py` module provides:

- asynchronous PostgreSQL connection via asyncpg;
- storage in the following tables:
  - `attacks`
  - `subscriptions`
- status change validation before saving;
- LISTEN / NOTIFY mechanism for real-time update delivery;
- user subscription management.

When a new record is inserted, a notification is automatically sent to the `attack_updates` channel.

### 3.6 Telegram Bot

The Telegram bot is implemented using the `python-telegram-bot` library in polling mode.

Main features:

- retrieving current region status (`/status`);
- subscription management (`/subscribe`, `/unsubscribe`, `/subscriptions`);
- receiving user reports (`/report`) with subsequent moderation;
- administrative commands (`/ban`, `/unban`, `/is_banned`, `/admin_message`, `/admin_report`).

The bot uses a separate database connection pool.

### 3.7 HTTP API

Endpoint:

```
GET /api/statuses/
```

Returns the aggregated status of all regions in JSON format.

Used for:

- initial map initialization;
- state recovery after connection loss.

### 3.8 WebSocket

Endpoint:

```
/ws/
```

Functions:

- maintaining active connections;
- sending a snapshot upon connection;
- broadcasting updates upon receiving PostgreSQL notifications;
- automatic client-side reconnection.

### 3.9 Frontend

The web interface is implemented using:

- MapTiler / OpenStreetMap;
- MapLibre GL / Leaflet;
- GeoJSON data for Russian regions.

Each region is assigned a color reflecting the aggregated threat level.

## 4. Project Structure

Main modules:

- main.py - initialization of FastAPI, WebSocket, listener, and bot;
- listener.py - message collection;
- analyzer.py - LLM interaction;
- db.py - PostgreSQL interaction;
- bot.py - Telegram bot logic;
- logger.py - centralized logging;
- frontend/ - client-side application;
- docker-compose.yml - container configuration;
- .env.example - environment variable configuration template.

## 5. Change Management

### 5.1 General Rules

- All changes are committed directly to the `main` branch.
- Local testing is required before applying changes.
- Modifications that break the LLM response format or database structure without compatibility validation are not allowed.

### 5.2 Modifying Classification Logic

When updating `analyzer.py`, it is required to:

- preserve the model’s output format;
- ensure correct handling of multiple events;
- verify compatibility with `process_message()`.

Changes to the LLM prompt must:

- preserve the strict response structure;
- exclude any free-form text outside the defined format;
- account for the complete list of Russian regions.

### 5.3 Adding a New Region

Required steps:

- add the region to the configuration list;
- update name mappings if necessary;
- verify correct map rendering;
- verify subscription handling.

### 5.4 Adding a New Threat Type

Required steps:

- update the list of allowed threat types;
- update map visualization logic;
- verify Telegram notification formatting;
- verify status aggregation logic.

### 5.5 Modifying the Telegram Bot

Before making changes:

- verify database impact;
- ensure correct administrator permission handling;
- test subscription and moderation workflows.

### 5.6 Testing Procedure

Recommended verification steps:

1. Retrieval of a message from a Telegram channel.
2. Correct classification.
3. Record persistence in the database.
4. Notification generation.
5. WebSocket update propagation.
6. Correct map rendering.
7. Telegram bot functionality.

Testing must include:

- single-event scenarios;
- multiple-event scenarios;
- messages containing banned words;
- duplicate messages.

## 6. Commit Requirements

Commits must:

- contain a concise and accurate description of the change;
- clearly reflect the essence of the modification (e.g., "fix LLM parsing", "add region normalization");
- avoid combining unrelated changes in a single commit;
- not include temporary debugging code.

## 7. Pre-Deployment Checklist

Before publishing changes, verify:

- syntax correctness and absence of runtime errors;
- preservation of the LLM response format;
- absence of duplicate database entries;
- correct WebSocket updates;
- correct map rendering;
- proper logging behavior;
- absence of confidential data in the source code.

## 8. Logging

Logging is implemented using the standard `logging` module.

Log levels:

- INFO
- WARNING
- ERROR

Log files rotate daily. Up to 30 archived files are retained.

## 9. Additional Information

The system is designed for continuous asynchronous operation and requires strict adherence to inter-component interaction formats. Changes in one module must be validated for compatibility with all other system components.

## 10. Licensing

The project is distributed under the MIT License. The full license text is available in the [LICENSE](LICENSE) file.