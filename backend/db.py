import asyncio
import os
from datetime import datetime
import pytz
from telegram import Bot
import asyncpg
from logger import logger
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", 1234),
    "database": os.getenv("DB_NAME", "attacks"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
}

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

_pool_main: asyncpg.Pool | None = None
_pool_bot: asyncpg.Pool | None = None
_schema_initialized = False
_schema_lock = asyncio.Lock()

async def _init_schema(pool: asyncpg.Pool):
    global _schema_initialized
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS attacks (
            id SERIAL PRIMARY KEY,
            region TEXT,
            attack_type TEXT,
            status TEXT,
            source TEXT,
            timestamp TEXT
        );
        """)

        await conn.execute("""
        CREATE OR REPLACE FUNCTION notify_attack_change()
        RETURNS trigger AS $$
        BEGIN
            PERFORM pg_notify('attack_updates', row_to_json(NEW)::text);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """)

        await conn.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'attack_insert_trigger'
            ) THEN
                CREATE TRIGGER attack_insert_trigger
                AFTER INSERT ON attacks
                FOR EACH ROW
                EXECUTE FUNCTION notify_attack_change();
            END IF;
        END;
        $$;
        """)

        await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_region_attack_type
        ON attacks(region, attack_type);
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            region TEXT,
            is_banned BOOLEAN DEFAULT FALSE,
            UNIQUE(user_id, region)
        );
        """)
    _schema_initialized = True
    logger.info("[DB] PostgreSQL initialization finished")

async def get_pool(is_bot: bool = False) -> asyncpg.Pool:
    global _pool_main, _pool_bot, _schema_initialized

    if is_bot:
        if _pool_bot is None:
            _pool_bot = await asyncpg.create_pool(
                **DB_CONFIG,
                max_inactive_connection_lifetime=30,
                loop=asyncio.get_running_loop()
            )
            logger.info("[DB] Connection pool created for BOT thread")
        return _pool_bot
    else:
        if _pool_main is None:
            _pool_main = await asyncpg.create_pool(
                **DB_CONFIG,
                max_inactive_connection_lifetime=30,
                loop=asyncio.get_running_loop()
            )
            logger.info("[DB] Connection pool created for MAIN thread")
        if not _schema_initialized:
            async with _schema_lock:
                if not _schema_initialized:
                    await _init_schema(_pool_main)
        return _pool_main

async def save_attack(region: str, attack_type: str, status: str, source: str = "manual", use_logger: bool = True, is_bot: bool = False):
    pool = await get_pool(is_bot=is_bot)
    timestamp = datetime.now(pytz.timezone("Europe/Moscow")).strftime("%H:%M:%S %d-%m-%Y")
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO attacks (region, attack_type, status, source, timestamp) VALUES ($1, $2, $3, $4, $5)",
            region, attack_type, status, source, timestamp
        )
    if use_logger:
        logger.info(f"[DB] Attack saved: {region} {attack_type} = {status} (source: {source})")

async def get_attacks_by_region(region: str, limit: int = 5, use_logger: bool = True, is_bot: bool = False):
    pool = await get_pool(is_bot=is_bot)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT attack_type, status, source, timestamp FROM attacks WHERE region=$1 ORDER BY id DESC LIMIT $2",
            region, limit
        )
    if use_logger:
        logger.info(f"[DB] Received last {len(rows)} attacks for {region}")
    return [tuple(row) for row in rows]

async def get_last_status(region: str, attack_type: str = None, use_logger: bool = True, is_bot: bool = False):
    pool = await get_pool(is_bot=is_bot)
    async with pool.acquire() as conn:
        if attack_type:
            row = await conn.fetchrow(
                "SELECT status FROM attacks WHERE region=$1 AND attack_type=$2 ORDER BY id DESC LIMIT 1",
                region, attack_type
            )
        else:
            rows = await conn.fetch(
                """
                SELECT attack_type, status
                FROM (
                    SELECT DISTINCT ON (attack_type) attack_type, status, id
                    FROM attacks
                    WHERE region = $1
                    ORDER BY attack_type, id DESC
                ) x
                """,
                region
            )
            result = {}
            for r in rows:
                result[r["attack_type"]] = r["status"]

            return {
                "region": region,
                "statuses": result,
            }
    if use_logger:
        logger.debug(f"[DB] Last status {attack_type} for {region}: {row['status'] if row else 'no data'}")
    return row['status'] if row else None

async def add_subscription(user_id: int, region: str, use_logger: bool = True, is_bot: bool = False) -> bool:
    pool = await get_pool(is_bot=is_bot)
    async with pool.acquire() as conn:
        result = await conn.execute(
            "INSERT INTO subscriptions (user_id, region) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            user_id, region
        )
    added = result == "INSERT 0 1"
    if use_logger:
        if added:
            logger.info(f"[DB] User {user_id} subscribed to {region}")
        else:
            logger.info(f"[DB] User {user_id} is already subscribed to {region}")
    return added

async def remove_subscription(user_id: int, region: str, use_logger: bool = True, is_bot: bool = False) -> bool:
    pool = await get_pool(is_bot=is_bot)
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM subscriptions WHERE user_id=$1 AND region=$2", user_id, region)
    if use_logger:
        logger.info(f"[DB] User {user_id} unsubscribed from {region}")
    return True

async def get_subscriptions(user_id: int, use_logger: bool = True, is_bot: bool = False):
    pool = await get_pool(is_bot=is_bot)
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT region FROM subscriptions WHERE user_id=$1", user_id)
    subscriptions = [r["region"] for r in rows]
    if use_logger:
        logger.info(f"User {user_id} has {len(subscriptions)} subscriptions")
    return subscriptions

async def get_users_by_region(region: str, use_logger: bool = True, is_bot: bool = False):
    pool = await get_pool(is_bot=is_bot)
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM subscriptions WHERE region=$1", region)
    users = [r["user_id"] for r in rows]
    if use_logger:
        logger.info(f"[DB] Found {len(users)} subscribers in {region}")
    return users

async def get_all_users(use_logger: bool = True, is_bot: bool = False):
    pool = await get_pool(is_bot=is_bot)
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT DISTINCT user_id FROM subscriptions")
    users = [r["user_id"] for r in rows]
    if use_logger:
        logger.info(f"[DB] Found {len(users)} total subscribers")
    return users

async def is_banned(user_id: int, use_logger: bool = True, is_bot: bool = False) -> bool:
    pool = await get_pool(is_bot=is_bot)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT 1 FROM subscriptions WHERE user_id=$1 AND is_banned=TRUE LIMIT 1", user_id
        )
    banned = row is not None
    if use_logger:
        logger.info(f"[DB] User {user_id} is {'banned' if banned else 'not banned'}")
    return banned

async def ban_user(user_id: int, reason: str = "<не указано>", use_logger: bool = True, is_bot: bool = False):
    if not await is_banned(user_id=user_id, use_logger=False, is_bot=is_bot):
        pool = await get_pool(is_bot=is_bot)
        async with pool.acquire() as conn:
            exist = await conn.fetchrow("SELECT 1 FROM subscriptions WHERE user_id=$1 LIMIT 1", user_id) is not None
            if exist: await conn.execute("UPDATE subscriptions SET is_banned=TRUE WHERE user_id=$1", user_id)
            else: await conn.execute("INSERT INTO subscriptions (user_id, is_banned) VALUES ($1, TRUE)", user_id)
        if use_logger:
            logger.info(f"[DB] User {user_id} banned. Reason: {reason}")
        try:
            await bot.send_message(chat_id=user_id, text=f"⚠️ Вы заблокированы администратором. Причина: {reason}")
        except Exception:
            logger.error(f"[TG/DB] Error sending to user {user_id}", exc_info=True)
    else:
        if use_logger:
            logger.info(f"[DB] User {user_id} is already banned")

async def unban_user(user_id: int, reason: str = "<не указано>", use_logger: bool = True, is_bot: bool = False):
    if await is_banned(user_id=user_id, use_logger=False, is_bot=is_bot):
        pool = await get_pool(is_bot=is_bot)
        async with pool.acquire() as conn:
            await conn.execute("UPDATE subscriptions SET is_banned=FALSE WHERE user_id=$1", user_id)
        if use_logger:
            logger.info(f"[DB] User {user_id} unbanned. Reason: {reason}")
        try:
            await bot.send_message(chat_id=user_id, text=f"⚠️ Вы разблокированы администратором. Причина: {reason}")
        except Exception:
            logger.error(f"[TG/DB] Error sending to user {user_id}", exc_info=True)
    else:
        if use_logger:
            logger.info(f"[DB] User {user_id} is not banned")
