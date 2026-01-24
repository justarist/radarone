import asyncio
import aiohttp
from typing import Optional, Iterable
from bs4 import BeautifulSoup
from config import TELEGRAM_CHANNELS, REGIONS, BANWORDS, ATTACK_TYPES, EXPANDED_ATTACK_TYPES, UB_ALLOWED_REGIONS
import db
from analyzer import analyze_message
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from notifications import format_notification
from logger import logger
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT = Bot(token=BOT_TOKEN)

REGION_MAP = {r.lower(): r for r in REGIONS}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/117.0 Safari/537.36"
    )
}

last_seen_messages = {}

def preprocess_message(message: str):
    msg_lower = message.lower()
    for banword in BANWORDS:
        if banword in msg_lower:
            logger.info(f"[LSNR] Message contains banword '{banword}', skipping.")
            return None
    return message

def normalize_region(name: str) -> Optional[str]:
    name_l = name.lower()

    if name_l in REGION_MAP:
        return REGION_MAP[name_l]

    for key, value in REGION_MAP.items():
        if name_l in key:
            return value

    return None

def expand_targets(region: str, attack_type: str, status: str) -> Iterable[tuple[str, str]]:
    targets = []

    if region != "Россия":
        if attack_type == "ALL" and status == "AC":
            targets.extend((region, at) for at in EXPANDED_ATTACK_TYPES)
        else:
            if attack_type == "UB" and region not in UB_ALLOWED_REGIONS:
                return []
            targets.append((region, attack_type))
    elif region == "Россия" and status == "AC":
        for r in REGIONS:
            if r == "Россия":
                continue
            if attack_type == "ALL":
                targets.extend((r, at) for at in EXPANDED_ATTACK_TYPES)
            else:
                if attack_type == "UB" and r not in UB_ALLOWED_REGIONS:
                    continue
                targets.append((r, attack_type))

    return targets

async def notify_users(users: list[int], text: str):
    async def send(user_id: int):
        try:
            await BOT.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "🌐 Открыть онлайн-карту",
                        web_app=WebAppInfo(url="https://radarone.online")
                    )]
                ])
            )
            await asyncio.sleep(0.05)
        except Exception:
            logger.exception(f"[TG] Failed to send to {user_id}")

    await asyncio.gather(*(send(uid) for uid in users))

async def handle_attack_update(
    region: str,
    attack_type: str,
    status: str,
    source: str,
    comment: Optional[str],
    is_bot: bool,
):
    last_status = await db.get_last_status(
        region=region,
        attack_type=attack_type,
        is_bot=is_bot
    )

    if last_status == status:
        return

    await db.save_attack(
        region=region,
        attack_type=attack_type,
        status=status,
        source=source,
        is_bot=is_bot
    )

    users = await db.get_users_by_region(region=region, is_bot=is_bot)
    if not users:
        return

    text = format_notification(region, attack_type, status, source, comment)
    await notify_users(users, text)

async def get_last_message(channel: str, session: aiohttp.ClientSession) -> Optional[dict]:
    url = f"https://t.me/s/{channel}"

    async with session.get(url, headers=HEADERS) as response:
        response.raise_for_status()
        html = await response.text()

    soup = BeautifulSoup(html, "html.parser")

    messages = soup.select("div.tgme_widget_message_text")
    if not messages:
        return None

    channel_title = soup.select_one("div.tgme_channel_info_header_title")

    return {
        "last_message": messages[-1].get_text("\n", strip=True),
        "channel_name": channel_title.get_text(strip=True) if channel_title else "<неизвестно>",
    }

async def process_message(
    message: str,
    channel_name: str,
    source: str,
    comment: str | None = None,
    is_bot: bool = False,
):
    message = preprocess_message(message)
    if not message:
        return

    try:
        result = analyze_message(message, channel_name=channel_name)
    except Exception:
        logger.error("[LSNR] Error while analyzing message")
        return

    for chunk in result.replace("\n", ",").split(","):
        parts = [p.strip() for p in chunk.split("/")]
        if len(parts) != 3:
            continue

        status, region_raw, attack_type = parts

        if attack_type not in ATTACK_TYPES:
            continue

        region = normalize_region(region_raw)
        if not region:
            continue

        targets = expand_targets(region, attack_type, status)
        for r, at in targets:
            await handle_attack_update(
                region=r,
                attack_type=at,
                status=status,
                source=source,
                comment=comment,
                is_bot=is_bot,
            )

async def listener_loop(poll_interval: int = 10):
    logger.info("[LSNR] Listener started (aiohttp + BS4)")

    async with aiohttp.ClientSession() as session:
        while True:
            tasks = []

            for channel in TELEGRAM_CHANNELS:
                tasks.append(get_last_message(channel, session))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for channel, result in zip(TELEGRAM_CHANNELS, results):
                if not result or isinstance(result, Exception):
                    continue

                message = result["last_message"]
                last = last_seen_messages.get(channel)

                if message == last:
                    continue

                last_seen_messages[channel] = message
                logger.info(f"[LSNR] New message from {channel}")

                await process_message(
                    message,
                    channel_name=result["channel_name"],
                    source=channel,
                )

            await asyncio.sleep(poll_interval)
