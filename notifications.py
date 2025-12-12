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
    attack_type = TYPE_LABEL.get(attack_type, attack_type)
    status = STATUS_READABLE.get(status, status)
    timestamp = datetime.now(pytz.timezone("Europe/Moscow")).strftime("%H:%M:%S %d-%m-%Y")
    source = f"@{source}" if source != "Admin" else source
    if status == "AC":
        result = (f"<b>✅ ОТБОЙ тревоги</b>\n"
            f"Регион: {region}\n"
            f"Тип угрозы: {attack_type}\n"
            f"Статус: {status}\n"
            f"Источник: {source}\n"
            f"Время: {timestamp}\n")
    else:
        result = (f"<b>⚠️ ВНИМАНИЕ!</b>\n"
            f"Угроза {attack_type}\n"
            f"Регион: {region}\n"
            f"Уровень: {status}\n"
            f"Источник: {source}\n"
            f"Время: {timestamp}\n")
    if comment:
        result += f"\n\n💬 Комментарий:\n<i>{comment}</i>"
    return result
