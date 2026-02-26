from openai import OpenAI
from ollama import Client
import openai
import os
from dotenv import load_dotenv
from config import REGIONS, TELEGRAM_CHANNELS
from logger import logger

load_dotenv()

def analyze_message(message: str, source: str, channel_name: str) -> str:
    prompt = f"""
Проанализируй следующий текст и выдай результат СТРОГО в формате:

[УРОВЕНЬ]/[РЕГИОН]/[ТИП ОПАСНОСТИ]

УРОВЕНЬ:  
- HD — высокий уровень опасности (по умолчанию для ракетной и воздушной тревоги, если не указано иное)  
- MD — повышенный уровень опасности (включая "внимание", "повышенная готовность")  
- AC — отмена тревоги или отсутствие угрозы

РЕГИОН:  
Выводи точное официальное название субъекта Российской Федерации.  
Если в сообщении указан город или населённый пункт, определи, к какому субъекту он относится, и выведи именно субъект РФ.  
Разрешается использовать только следующие названия (в точности как написано, без изменений):  
$1
$2
ТИП ОПАСНОСТИ:  
Только одно из: UAV, AIR, ROCKET, UB, ALL

$3
СОКРАЩЕНИЯ:
UAV - беспилотный летательный аппарат, БПЛА  
AIR - воздушная опасность  
ROCKET - ракетная опасность  
UB - безэкипажный катер
ALL - все опасности.
         
ПРАВИЛА:
- САМОЕ ГЛАВНОЕ: Сообщения, не содержащие необходимой информации, игнорировать (выводить пустую строку).
- Для ракетной и воздушной опасности по умолчанию уровень HD, если не указано иное.  
- Если тревога отменена, использовать AC.  
- Если сообщение содержит "внимание", "повышенная готовность" и подобные — использовать MD.  
- Если несколько регионов — вывести для каждого отдельную запись через запятую без пробела после запятой (например: MD/Рязанская область/UAV,HD/Республика Мордовия/UAV).  
- Использовать только символ "/" для разделения.  
- Выводить только итоговую строку, без лишних слов, кавычек и пояснений.
- Если написано "наблюдается сбитие", "пролетают" и т.п., то уровень HD.
- Если сначала написано "БПЛА пролетают регион N", а затем "Регион M на подлете", то означает, что в обоих регионах атака БПЛА (UAV), при этом у региона М средняя опасность, у региона N - высокая
- Если сообщение содержит формулировки вроде "тишина", "чистое небо", "регион чисто", "угрозы не фиксируются", "не фиксируем угроз", "угроз нет", трактовать это как AC (отсутствие угроз) и ALL (все угрозы), например AC/Брянская область/ALL.
- Если формулировки вроде "тишина", "чистое небо", "угрозы не фиксируются", "не фиксируем угроз", "угроз нет" указаны глобально ("по всей России", "угроз не фиксируется по стране") — выдать AC (отсутствие угроз) и ALL (все угрозы) для региона "Россия".
- МВШ (малый воздушный шар) квалифицировать как Воздушную угрозу (AIR)

Текст для анализа:  
{message}
"""
    if source and source in TELEGRAM_CHANNELS: prompt = prompt.replace("$1", f"{", ".join(REGIONS[source])}\n")
    else: prompt = prompt.replace("$1", f"{", ".join(REGIONS["all"])}\n")

    if "Россия" in REGIONS[source] or not source: prompt = prompt.replace("$2", "Регион \"Россия\" использовать только при глобальных уведомлениях (например, \"по всей России\", \"угроз не фиксируется по стране\") и зачастую только для AC.\n")
    else: prompt = prompt.replace("$2", "")

    if channel_name and channel_name not in ["@radaronebot (/report)", "Admin"]: prompt = prompt.replace("$3", f"НАЗВАНИЕ ТЕЛЕГРАМ-КАНАЛА (используй для формирования более корректного названия): {channel_name}\n")
    else: prompt = prompt.replace("$3", "")

    try:
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        logger.info(f"[GPT] Analyzing message using OpenAI")
        response = openai_client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": "ЧЕТКО СЛЕДУЙ ИНСТРУКЦИЯМ, ДАННЫМ В СООБЩЕНИИ"},
                {"role": "user", "content": prompt}
            ]
        )
        result = response.choices[0].message.content.strip()
        logger.info(f"[GPT] Analysis result: {result}")
        return result

    except Exception as openai_error:
        if isinstance(openai_error, openai.RateLimitError): logger.error("[GPT] Error in analyze_message(), rate limit exceeded — trying Ollama")
        elif isinstance(openai_error, openai.PermissionDeniedError): logger.error("[GPT] Error in analyze_message(), unsupported request country — trying Ollama")
        elif isinstance(openai_error, openai.AuthenticationError): logger.error("[GPT] Error in analyze_message(), authentication error — trying Ollama")
        else: logger.error("[GPT] Error in analyze_message() — trying Ollama", exc_info=True)

        try:
            ollama_model = os.getenv("OLLAMA_MODEL")
            logger.info(f"[OLLAMA] Sending request to Ollama (model {ollama_model})")
            ollama_client = Client(
                host="https://ollama.com",
                headers={"Authorization": f"Bearer {os.getenv("OLLAMA_API_KEY")}"}
            )
            messages = [
                {
                    'role': 'user',
                    'content': "ЧЕТКО СЛЕДУЙ ИНСТРУКЦИЯМ, ДАННЫМ В СООБЩЕНИИ\n" + prompt,
                },
            ]

            result = ""
            for part in ollama_client.chat(ollama_model, messages=messages, stream=True):
                result += f"{part['message']['content']}\n"
            result = result.replace("\n", "")
            logger.info(f"[OLLAMA] Analysis result: {result}")
            return result

        except Exception as ollama_error:
            logger.error("[OLLAMA] Critical error while using Ollama", exc_info=True)
            return "AC/Россия/ALL"
