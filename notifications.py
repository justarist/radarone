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
    if status == "AC":
        result = f"""
            <b>✅ ОТБОЙ тревоги</b>\n
            Регион: {region}\n
            Тип угрозы: {attack_type}\n
            Статус: {status}\n
            Источник: @{source}\n
            Время: {timestamp}
        """
    else:
        result = f"""
            <b>⚠️ ВНИМАНИЕ!</b>\n
            Угроза {attack_type}\n
            Регион: {region}\n
            Уровень: {status}\n
            Источник: @{source}\n
            Время: {timestamp}
        """
    if comment:
        result += f"\n\n<i>💬 Комментарий: {comment}</i>"
    return result
