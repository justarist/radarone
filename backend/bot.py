from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, ConversationHandler, filters
from config import REGIONS, TELEGRAM_CHANNELS
from dotenv import load_dotenv
from logger import logger
import os
import db
from time import sleep
import pytz
from listener import process_message

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

REPORT_WAITING = 1
REGIONS_PER_PAGE = 10

async def send_region_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page = 0, array = REGIONS, command = "subscribe", last_command = "`/subscribe all` - подписаться на все регионы"):
    total_pages = (len(array) - 1) // REGIONS_PER_PAGE + 1
    start = page * REGIONS_PER_PAGE
    end = start + REGIONS_PER_PAGE
    regions = array[start:end]

    text_lines = [f"📍 Выбери регион (стр. {page+1}/{total_pages}):\n"]
    for r in regions:
        if r != "Россия": text_lines.append(f"`/{command} {r}`")
        else: text_lines.append(f"{last_command}")

    text = "\n".join(text_lines)

    keyboard = []
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅ Назад", callback_data=f"{command}_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ➡", callback_data=f"{command}_page_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    else:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_report":
        context.user_data["report_cancelled"] = True
        logger.info(f"[BOT] User {update.effective_user.id} cancelled sending message in /report")
        await update.callback_query.edit_message_text("❌ Действие отменено.")
        sleep(5)
        await update.callback_query.message.delete()
        return ConversationHandler.END
    
    if query.data.startswith("approve_") or query.data.startswith("reject_"):
        action, msg_id = query.data.split("_", 1)
        msg_key = f"report_{msg_id}"
        data = context.bot_data.get(msg_key)
        user_id = data["original_user_id"]
        timestamp = data["timestamp"]

        if not data:
            await query.edit_message_text("⚠️ Не удалось найти сообщение.")
            return

        if data.get("handled"):
            await query.answer(text="⚠️ Это сообщение уже было обработано другим администратором.", show_alert=True)
            await query.edit_message_text(f"🆔 User ID: <a href='tg://user?id={user_id}'>{user_id}</a>\n⌛️ Sending time: <code>{timestamp}</code>\n⚠️ Это сообщение уже было обработано другим администратором.", parse_mode="HTML")
            return
        
        data["handled"] = True
        context.bot_data[msg_key] = data
        original_message = data["original_message"]

        if action == "approve":
            await query.edit_message_text(f"🆔 User ID: <a href='tg://user?id={user_id}'>{user_id}</a>\n⌛️ Sending time: <code>{timestamp}</code>\n✅ Message has been approved and will be used by the system.", parse_mode="HTML")
            logger.info(f"[BOT] Admin {update.effective_user.id} approved message in /report (msg_id: {msg_id})")
            await process_message(message=original_message, channel_name="Admin", source="radaronebot (/report)", is_bot=True)
        elif action == "reject":
            await query.edit_message_text(f"🆔 User ID: <a href='tg://user?id={user_id}'>{user_id}</a>\n⌛️ Sending time: <code>{timestamp}</code>\n❌ Message has been rejected.", parse_mode="HTML")
            logger.info(f"[BOT] Admin {update.effective_user.id} rejected message in /report (msg_id: {msg_id})")
        else:
            await query.edit_message_text("❓ Unsupported action.")
        return

    data = query.data or ""
    parts = data.split("_page_")
    if len(parts) != 2:
        await query.edit_message_text("❓ Неподдерживаемое действие.")
        return

    command = parts[0]
    try:
        page = int(parts[1])
    except ValueError:
        await query.edit_message_text("❓ Неверный номер страницы.")
        return

    if command == "subscribe":
        await send_region_page(update, context, page, REGIONS, "subscribe", "`/subscribe all` - подписаться на все регионы")
    elif command == "unsubscribe":
        subscriptions = await db.get_subscriptions(user_id=update.effective_user.id, is_bot=True)
        if not subscriptions:
            await query.edit_message_text("❌ У тебя нет активных подписок.")
            return
        await send_region_page(update, context, page, subscriptions, "unsubscribe", "`/unsubscribe all` - отписаться от всех регионов")
    elif command == "status":
        await send_region_page(update, context, page, REGIONS, "status", "")

async def _set_commands(app):
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("help", "Список команд"),
        BotCommand("status", "Последние события по региону"),
        BotCommand("subscribe", "Подписаться на регион"),
        BotCommand("unsubscribe", "Отписаться от региона"),
        BotCommand("subscriptions", "Мои подписки"),
        BotCommand("report", "Сообщить об атаке на регион"),
        BotCommand("channels", "Список анализируемых каналов"),
        BotCommand("about", "О нас")
    ]
    await app.bot.set_my_commands(commands)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"[BOT] User {update.effective_user.id} called /start")
    await update.message.reply_text(
        "👋 Привет! Это бот для мониторинга тревог Радар ONE.\n\n"
        "Используй /help для списка команд.\n"
        "Важно: перед тем как ждать уведомления — нажми /start и /subscribe <регион>."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"[BOT] User {update.effective_user.id} called /help")
    await update.message.reply_text(
        "📌 Команды:\n"
        "/start — запустить бота\n"
        "/help — список команд\n"
        "/status <регион> — последние события по региону\n"
        "/subscribe <регион> — подписаться на уведомления\n"
        "/unsubscribe <регион> — отменить подписку\n"
        "/subscriptions — показать ваши подписки\n"
        "/report — сообщить об атаке на регион\n"
        "/channels — каналы, сообщения которых используются нашим ботом\n"
        "/about — о нас и о нашем боте\n"
        "Используйте официальные названия регионов (например: Москва, Калужская область)."
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):  
    if context.args:
        region = " ".join(context.args)
        if region not in REGIONS:
            for i in range(len(REGIONS)):
                if region.lower() in (REGIONS[i]).lower():
                    region = REGIONS[i]
                    break
            if region not in REGIONS:
                logger.warning(f"[BOT] User {update.effective_user.id} requested unknown region: {region}")
                await update.message.reply_text("⚠ Регион не найден. Используй официальное название.")
                return

        events = await db.get_attacks_by_region(region=region, limit=5, is_bot=True)
        if not events:
            await update.message.reply_text(f"В регионе {region} пока нет записей.")
            return

        reply = [f"📍 {region}\n"]
        for attack_type, status_, source, timestamp in events:
            reply.append(f"➡ {timestamp}: {attack_type.replace('UAV', 'БПЛА').replace('AIR', 'Воздушная').replace('ROCKET', 'Ракетная').replace('UB', 'БЭК')} — {status_.replace('AC', 'Отбой').replace('MD', 'Средний').replace('HD', 'Высокий')} (Источник: @{source})")

        logger.info(f"[BOT] User {update.effective_user.id} requested status for {region}")
        await update.message.reply_text("\n".join(reply))
        return

    await send_region_page(update, context, 0, REGIONS, "status", "")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if " ".join(context.args) == "all":
        for region in REGIONS:
            if region != "Россия": added = await db.add_subscription(user_id=update.effective_user.id, region=region, use_logger=False, is_bot=True)
        logger.info(f"[BOT] User {update.effective_user.id} subscribed to all regions")
        await update.message.reply_text(f"✅ Ты подписался на все регионы")
        return
    elif context.args:
        region = " ".join(context.args)
        if region not in REGIONS:
            for i in range(len(REGIONS)):
                if region.lower() in (REGIONS[i]).lower():
                    region = REGIONS[i]
                    break
            if region not in REGIONS:
                logger.warning(f"[BOT] User {update.effective_user.id} attempted to subscribe to a non-existent region: {region}")
                await update.message.reply_text("⚠ Регион не найден. Используй официальное название.")
                return
        added = await db.add_subscription(user_id=update.effective_user.id, region=region, is_bot=True)
        if added:
            await update.message.reply_text(f"✅ Ты подписался на {region}")
        else:
            await update.message.reply_text(f"ℹ Ты уже подписан на {region}")
        return

    await send_region_page(update, context)

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscriptions = await db.get_subscriptions(user_id=update.effective_user.id, use_logger=False, is_bot=True)
    if " ".join(context.args) == "all":
        for region in subscriptions:
            if region != "Россия":
                await db.remove_subscription(user_id=update.effective_user.id, region=region, use_logger=False, is_bot=True)
        logger.info(f"[BOT] User {update.effective_user.id} unsubscribed from all regions")
        await update.message.reply_text(f"❌ Подписка на все регионы отменена")
        return
    elif context.args:
        region = " ".join(context.args)
        if region not in REGIONS:
            for i in range(len(REGIONS)):
                if region.lower() in (REGIONS[i]).lower():
                    region = REGIONS[i]
                    break
        await db.remove_subscription(user_id=update.effective_user.id, region=region, is_bot=True)
        await update.message.reply_text(f"❌ Подписка на {region} отменена")
        return
    elif not subscriptions:
        await update.message.reply_text("❌ У тебя нет активных подписок.")
        return
    
    await send_region_page(update, context, 0, subscriptions, "unsubscribe", "`/unsubscribe all` - отписаться от всех регионов")

async def subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscriptions = await db.get_subscriptions(user_id=update.effective_user.id, is_bot=True)
    if not subscriptions:
        await update.message.reply_text("У тебя нет подписок.")
    else:
        logger.info(f"[BOT] User {update.effective_user.id} requested list of subscriptions")
        await update.message.reply_text("📍 Твои подписки:\n" + "\n".join(subscriptions))

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ <b>О боте</b>\n\n"
        "Этот бот создан для оперативного мониторинга сообщений о тревогах и происшествиях в разных регионах.\n\n"
        "📡 Он автоматически отслеживает обновления из множества проверенных телеграм-каналов и источников в реальном времени. "
        "Когда появляется новое сообщение о тревоге, воздушной опасности, прилётах или других инцидентах — "
        "бот сохраняет информацию и уведомляет подписчиков соответствующих регионов.\n\n"
        "🔔 Ты можешь подписаться на один или несколько регионов, чтобы получать уведомления только по нужным направлениям.\n\n"
        "⚠️Бот не является официальным источником данных, однако помогает быстро узнавать о событиях, "
        "используя автоматический сбор и анализ сводок из открытых источников.\n\n"
        "👨‍💻 Разработано с упором на стабильность, простоту и максимальную скорость доставки уведомлений.\n\n"
        "📢 Разработчики: <a href='https://t.me/radaroneteam'>@radaroneteam</a>"
    , parse_mode="HTML")
    logger.info(f"[BOT] User {update.effective_user.id} called /about")

async def channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "💬 Телеграм-каналы, сообщения из которых используются для анализа и оповещения пользователей:\n"
    for ch in TELEGRAM_CHANNELS: text += f"    ➽ @{ch}\n"
    await update.message.reply_text(text, parse_mode="HTML")
    logger.info(f"[BOT] User {update.effective_user.id} called /channels")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await db.is_banned(user_id=update.effective_user.id, use_logger=False, is_bot=True):
        logger.warning(f"[BOT] Banned user {update.effective_user.id} attempted to call /report")
        await update.message.reply_text("<i>❌ Вы не можете использовать /report, данная функция отключена у вас из-за многочисленных нарушений.\n\n❓ По вопросам включения/отключения этой функции и другим вопросам обращайтесь в личные сообщения (direct messages) Телеграм-канала @radaroneteam</i>", parse_mode="HTML")
        return ConversationHandler.END
    logger.info(f"[BOT] User {update.effective_user.id} called /report")
    context.user_data["report_cancelled"] = False
    await update.message.reply_text(
        text=
        "❗️ Сообщите нам о тревогах, пролетах БПЛА, работе ПВО и т.п. для того, чтобы мы лучше и эффективнее работали.\n\n"
        "⏩ Для сообщения об этом, напишите следующее сообщение и оно будет отправлено администраторам на проверку. После прохождения проверки сообщение будет автоматически проанализировано и будет установлен соответствующий режим опасности в определенном регионе.\n\n"
        "🚫 Не отправляйте сообщения, которые не содержат типа угрозы и местополжения, иначе ваше сообщение не будет учтено.\n\n"
        "⛔️ Если вы будете спамить, отправлять сообщения, не содержащие необходимой информации, и так далее, функция будет отключена у вас из-за многочисленных нарушений.\n\n"
        "👁‍🗨 По вопросам работы бота обращайтесь в личные сообщения (direct messages) канала @radaroneteam.\n",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚫 Отмена", callback_data=f"cancel_report")]]),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    return REPORT_WAITING

async def handle_report_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("report_cancelled"): return ConversationHandler.END

    user_message = update.message.text
    user_id = update.effective_user.id
    message_time = update.message.date

    admin_user_ids = os.getenv("ADMIN_USER_ID").split(",")

    for admin_user_id in admin_user_ids:
        forwarded_message = await context.bot.forward_message(
            chat_id=admin_user_id,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )

        context.bot_data[f"report_{forwarded_message.message_id}"] = {
            "original_user_id": user_id,
            "original_message": user_message,
            "timestamp": message_time.astimezone(pytz.timezone("Europe/Moscow")).strftime('%H:%M:%S %d-%m-%Y'),
            "handled": False
        }

        approval_buttons = [
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{forwarded_message.message_id}")],
            [InlineKeyboardButton("❌ Reject", callback_data=f"reject_{forwarded_message.message_id}")]
        ]

        await context.bot.send_message(
            admin_user_id,
            text=(
                f"🆔 User ID: <a href='tg://user?id={user_id}'>{user_id}</a>\n"
                f"⌛️ Sending time: <code>{message_time.astimezone(pytz.timezone("Europe/Moscow")).strftime('%H:%M:%S %d-%m-%Y')}</code>"
            ),
            reply_markup=InlineKeyboardMarkup(approval_buttons),
            parse_mode="HTML"
        )

    await update.message.reply_text("✅ Ваше сообщение отправлено на проверку.")
    logger.info(f"[BOT] User {update.effective_user.id}'s message has been sent for verification to admin.")
    return ConversationHandler.END

async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_answer = " ".join(context.args).split(" ", 1)
    if str(update.effective_user.id) not in os.getenv("ADMIN_USER_ID").split(","):
        logger.warning(f"[BOT] User {update.effective_user.id} attempted to use /ban without admin permissions.")
        return
    try:
        user_id = int(user_answer[0])
        if not(await db.is_banned(user_id=user_id, use_logger=False, is_bot=True)):
            await db.ban_user(user_id=user_id, reason=user_answer[1], is_bot=True)
            logger.info(f"[BOT] Admin {update.effective_user.id} banned user {user_id} via /ban.")
        else:
            logger.info(f"[BOT] Admin {update.effective_user.id} attempted to ban already banned user {user_id} via /ban.")
    except Exception as e:
        logger.error(f"[BOT] Admin {update.effective_user.id} attempted to ban user {user_answer[0]} via /ban but something went wrong", exc_info=True)

async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_answer = " ".join(context.args).split(" ", 1)
    if str(update.effective_user.id) not in os.getenv("ADMIN_USER_ID").split(","):
        logger.warning(f"[BOT] User {update.effective_user.id} attempted to use /unban without admin permissions.")
        return
    try:
        user_id = int(user_answer[0])
        if await db.is_banned(user_id=user_id, use_logger=False, is_bot=True):
            await db.unban_user(user_id=user_id, reason=user_answer[1], is_bot=True)
            logger.info(f"[BOT] Admin {update.effective_user.id} unbanned user {user_id} via /unban.")
        else:
            logger.info(f"[BOT] Admin {update.effective_user.id} attempted to unban already unbanned user {user_id} via /unban.")
    except Exception as e:
        logger.error(f"[BOT] Admin {update.effective_user.id} attempted to unban user {user_answer[0]} via /unban but something went wrong", exc_info=True)

async def admin_is_banned(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_answer = context.args
    if str(update.effective_user.id) not in os.getenv("ADMIN_USER_ID").split(","):
        logger.warning(f"[BOT] User {update.effective_user.id} attempted to use /is_banned without admin permission.")
        return
    try:
        user_id = int(user_answer[0])
        await update.message.reply_text(
            f"Пользователь {user_id} {'заблокирован' if await db.is_banned(user_id=user_id, use_logger=False, is_bot=True) else 'не заблокирован'}"
        )
        logger.info(f"[BOT] Admin {update.effective_user.id} called /is_banned for user {user_id}")
    except Exception as e:
        logger.error(f"[BOT] Admin {update.effective_user.id} attempted to use /is_banned for user {user_answer[0]} but something went wrong", exc_info=True)

async def admin_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_answer = " ".join(context.args).split(";", 1)
    message = user_answer[0].replace("\\n", "\n")
    comment = user_answer[1].replace("\\n", "\n") if user_answer[1] else None
    if str(update.effective_user.id) not in os.getenv("ADMIN_USER_ID").split(","):
        logger.warning(f"[BOT] User {update.effective_user.id} attempted to use /admin_report without admin permissions.")
        return
    try:
        await process_message(message=message, channel_name="Admin", source="Admin", comment=comment, is_bot=True)
        logger.info(f"[BOT] Admin {update.effective_user.id} sent report via /admin_report.")
    except Exception as e:
        logger.error(f"[BOT] Admin {update.effective_user.id} attempted to send report via /admin_report but something went wrong", exc_info=True)

async def admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in os.getenv("ADMIN_USER_ID").split(","):
        logger.warning(f"[BOT] User {update.effective_user.id} attempted to use /admin_message without admin permissions.")
        return
    try:
        if context.args:
            message = " ".join(context.args).replace("\\n", "\n")
            for user_id in await db.get_all_users(is_bot=True):
                await context.bot.send_message(chat_id=user_id, text=f"<b>🔔 ВНИМАНИЕ!</b>\n💬 Сообщение от администратора:\n<blockquote>{message}</blockquote>", parse_mode="HTML")
                logger.info(f"[BOT] Admin {update.effective_user.id} sent message to all users via /admin_message.")
        else:
            logger.warning(f"[BOT] Admin {update.effective_user.id} attempted to send empty message via /admin_message but nothing was provided.")
    except Exception as e:
        logger.error(f"[BOT] Admin {update.effective_user.id} attempted to send message to all users via /admin_message but something went wrong", exc_info=True)

def main():
    application = Application.builder().token(BOT_TOKEN).post_init(_set_commands).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("subscriptions", subscriptions))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(CommandHandler("channels", channels))
    application.add_handler(CommandHandler("ban", admin_ban))
    application.add_handler(CommandHandler("unban", admin_unban))
    application.add_handler(CommandHandler("is_banned", admin_is_banned))
    application.add_handler(CommandHandler("admin_report", admin_report))
    application.add_handler(CommandHandler("admin_message", admin_message))
    application.add_handler(CallbackQueryHandler(handle_button_click, pattern=r"^(subscribe|unsubscribe|status)_page_"))
    application.add_handler(CallbackQueryHandler(handle_button_click))
    
    report_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("report", report)],
        states={
            REPORT_WAITING: [
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_report_response)
            ],
        },
        fallbacks=[],
    )

    application.add_handler(report_conv_handler)
    logger.info("[BOT] Bot started (polling)...")
    application.run_polling(stop_signals=[])
