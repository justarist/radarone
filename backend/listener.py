import asyncio
from bs4 import BeautifulSoup
import requests
from config import telegram_channels, region_names
import db
from analyzer import analyze_message
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from notifications import format_notification
from logger import logger
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

last_seen_messages = {}

def get_last_message(channel_name: str):
    url = f"https://t.me/s/{channel_name}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/117.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    messages = soup.find_all("div", class_="tgme_widget_message_text")
    if not messages:
        return None
    return messages[-1].get_text("\n", strip=True)

async def process_message(message: str, source: str = "<неизвестно>", comment: str = None, is_bot: bool = False):
    try:
        result = analyze_message(message)
    except Exception as e:
        logger.error("[LSNR] Error while analyzing message", exc_info=True)
        return

    for split_message in result.replace("\n", ",").split(","):
        parts = split_message.strip().split("/")
        if len(parts) != 3:
            logger.warning(f"[LSNR] Invalid format from model: {split_message}")
            continue
        status, region_name, attack_type = parts
        region_name = region_name.strip()
        if attack_type not in ["UAV", "AIR", "ROCKET", "UB", "ALL"]:
            logger.warning(f"[LSNR] Unknown attack type: {attack_type}")
            continue
        if region_name not in region_names:
            for i in range(len(region_names)):
                if region_name.lower() in (region_names[i]).lower():
                    region_name = region_names[i]
                    break
            if region_name not in region_names:
                logger.warning(f"[LSNR] Unknown region: {region_name}")
                continue
        
        if region_name != "Россия":
            if attack_type != "ALL":
                last_status = await db.get_last_status(region=region_name, attack_type=attack_type, is_bot=is_bot)
                if last_status == status:
                    logger.info(f"[LSNR] Repeat (skipping): {region_name} {attack_type} = {status}")
                    continue
            
                await db.save_attack(region=region_name, attack_type=attack_type, status=status, source=source, is_bot=is_bot)

                users = await db.get_users_by_region(region=region_name, is_bot=is_bot)
                if not users:
                    continue

                text = format_notification(region_name, attack_type, status, source, comment)
                for user_id in users:
                    try:
                        await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🌐 Открыть онлайн-карту", web_app=WebAppInfo(url="https://radarone.online"))]]))
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        logger.error(f"[LSNR] Error sending to user {user_id}", exc_info=True)
            elif attack_type == "ALL" and status == "AC":
                for attack_type in ["UAV", "AIR", "ROCKET", "UB"]:
                    last_status = await db.get_last_status(region=region_name, attack_type=attack_type, is_bot=is_bot)
                    if last_status == status:
                        logger.info(f"[LSNR] Repeat (skipping): {region_name} {attack_type} = {status}")
                        continue
            
                    await db.save_attack(region=region_name, attack_type=attack_type, status=status, source=source, is_bot=is_bot)

                    users = await db.get_users_by_region(region=region_name, is_bot=is_bot)
                    if not users:
                        continue

                    text = format_notification(region_name, attack_type, status, source, comment)
                    for user_id in users:
                        try:
                            await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🌐 Открыть онлайн-карту", web_app=WebAppInfo(url="https://radarone.online"))]]))
                            await asyncio.sleep(0.05)
                        except Exception as e:
                            logger.error(f"[LSNR] Error sending to user {user_id}", exc_info=True)
        elif region_name == "Россия" and status == "AC":
            for region_name in region_names:
                if region_name == "Россия":
                    continue

                if attack_type != "ALL":
                    last_status = await db.get_last_status(region=region_name, attack_type=attack_type, is_bot=is_bot)
                    if last_status == status:
                        logger.info(f"[LSNR] Repeat (skipped): {region_name} {attack_type} = {status}")
                        continue
                
                    await db.save_attack(region=region_name, attack_type=attack_type, status=status, source=source, is_bot=is_bot)

                    users = await db.get_users_by_region(region=region_name, is_bot=is_bot)
                    if not users:
                        logger.info(f"[LSNR] No subscribers for region {region_name}")
                        continue

                    text = format_notification(region_name, attack_type, status, source, comment)
                    for user_id in users:
                        try:
                            await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🌐 Открыть онлайн-карту", web_app=WebAppInfo(url="https://radarone.online"))]]))
                            await asyncio.sleep(0.05)
                        except Exception as e:
                            logger.error(f"[LSNR] Error sending to user {user_id}", exc_info=True)
                elif attack_type == "ALL":
                    for attack_type in ["UAV", "AIR", "ROCKET", "UB"]:
                        last_status = await db.get_last_status(region=region_name, attack_type=attack_type, is_bot=is_bot)
                        if last_status == status:
                            logger.info(f"[LSNR] Repeat (skipped): {region_name} {attack_type} = {status}")
                            continue
                
                        await db.save_attack(region=region_name, attack_type=attack_type, status=status, source=source, is_bot=is_bot)

                        users = await db.get_users_by_region(region=region_name, is_bot=is_bot)
                        if not users:
                            continue

                        text = format_notification(region_name, attack_type, status, source, comment)
                        for user_id in users:
                            try:
                                await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🌐 Открыть онлайн-карту", web_app=WebAppInfo(url="https://radarone.online"))]]))
                                await asyncio.sleep(0.05)
                            except Exception as e:
                                logger.error(f"[TG/LSNR] Error sending to user {user_id}", exc_info=True)

                    attack_type = "ALL"

async def listener_loop(poll_interval: int = 10):
    logger.info("[LSNR] Listener started - reading channels via BS4")
    while True:
        for channel in telegram_channels:
            try:
                message = get_last_message(channel)
                if not message:
                    continue
                last_message = last_seen_messages.get(channel)
                if message == last_message:
                    continue
                last_seen_messages[channel] = message
                logger.info(f"[LSNR] New message from {channel}:\n{message[:100]}...")
                await process_message(message, source=channel)
            except Exception as e:
                logger.error(f"[LSNR] Error while processing message from {channel}", exc_info=True)
        await asyncio.sleep(poll_interval)
