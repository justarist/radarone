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
        result = f"""
        <b>✅ ОТБОЙ тревоги</b>
        Регион: {region}
        Тип угрозы: {attack_type}
        Статус: {status}
        Источник: {source}
        Время: {timestamp}"""
    else:
        result = f"""
        <b>⚠️ ВНИМАНИЕ!</b>
        Угроза {attack_type}
        Регион: {region}
        Уровень: {status}
        Источник: {source}
        Время: {timestamp}"""
    if comment:
        result += f"\n💬 Комментарий: <i>{comment}</i>"
    return result
