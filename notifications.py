from datetime import datetime
import pytz

TYPE_LABEL = {
    "UAV": "атаки БПЛА",
    "AIR": "воздушной атаки",
    "ROCKET": "ракетной атаки",
    "UB": "атаки безэкипажного катера (БЭК)"
}

STATUS_READABLE = {
    "HD": "Высокий",
    "MD": "Средний",
    "AC": "Отбой/Нет угрозы"
}

def format_notification(region: str, attack_type: str, status: str, source: str, comment: str = None) -> str:
    rattack_type = TYPE_LABEL.get(attack_type, attack_type)
    rstatus = STATUS_READABLE.get(status, status)
    timestamp = datetime.now(pytz.timezone("Europe/Moscow")).strftime("%H:%M:%S %d-%m-%Y")
    source = f"@{source}" if source != "Admin" else source
    if status == "AC":
        result = (f"<b>✅ ОТБОЙ тревоги</b>\n"
            f"Регион: {region}\n"
            f"Тип угрозы: {rattack_type}\n"
            f"Статус: {rstatus}\n"
            f"Источник: {source}\n"
            f"Время: {timestamp}\n")
    else:
        result = (f"<b>⚠️ ВНИМАНИЕ!</b>\n"
            f"Угроза {rattack_type}\n"
            f"Регион: {region}\n"
            f"Уровень: {rstatus}\n"
            f"Источник: {source}\n"
            f"Время: {timestamp}\n")
    if comment:
        result += f"\n💬 Комментарий:\n<blockquote>{comment}</blockquote>"
    return result
