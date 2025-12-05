from datetime import datetime

TYPE_LABEL = {
    "UAV": "атаки БПЛА",
    "AIR": "воздушной атаки",
    "ROCKET": "ракетной атаки",
    "UB": "атаки безэкипажного катера (БЭК)"
}

LEVEL_READABLE = {
    "HD": "Высокий",
    "MD": "Средний",
    "AC": "Отбой/Нет угрозы"
}

def format_notification(region: str, danger_type: str, level: str, source: str) -> str:
    tlabel = TYPE_LABEL.get(danger_type, danger_type)
    lread = LEVEL_READABLE.get(level, level)
    ts = datetime.now().strftime("%H:%M:%S %d-%m-%Y")
    if level == "AC":
        return (
            f"✅ ОТБОЙ тревоги\n"
            f"Регион: {region}\n"
            f"Тип угрозы: {tlabel}\n"
            f"Статус: {lread}\n"
            f"Источник: @{source}\n"
            f"Время: {ts}"
        )
    else:
        return (
            f"⚠️ ВНИМАНИЕ!\n"
            f"Угроза {tlabel}\n"
            f"Регион: {region}\n"
            f"Уровень: {lread}\n"
            f"Источник: @{source}\n"
            f"Время: {ts}"
        )
