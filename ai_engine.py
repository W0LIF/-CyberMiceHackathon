import os
import requests
import urllib3
import json
from parsing.universal_parser import UniversalParser, CONFIGURATIONS as PARSER_CONFIGS

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) #отключение предупреждений на гос сайтах

from langchain_core.messages import AIMessage, HumanMessage
from langchain_gigachat.chat_models import GigaChat
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import tool

GIGACHAT_CREDENTIALS = "MDE5YWJiZTMtNjFhMi03YjQ2LWE0ZWYtZGZhMmQzYjg0OGUyOmU3OTIwZmE5LWY2MjUtNGExMy1hYmNkLWI1Y2NkNzc4N2M2NQ=="

BASE_URL = "https://yazzh.gate.petersburg.ru"

API_CATALOG = {
    # Животные
    "pets": [
        f"{BASE_URL}/mypets/all-category/",
        f"{BASE_URL}/mypets/posts/",
        f"{BASE_URL}/mypets/recommendations/"
        f"{BASE_URL}/mypets/animal-breeds/",
    ],
    # Документы и МФЦ
    "documents": [
        f"{BASE_URL}/mfc/all/"
    ],
    # Здоровье
    "health": [
        f"{BASE_URL}/polyclinics/"
    ],
    # Родитель
    "iparent": [
        f"{BASE_URL}/iparent/places/categoria/",
        f"{BASE_URL}/dou/", 
        f"{BASE_URL}/dou/available-spots/",
        f"{BASE_URL}/dou/commissions/",
         f"{BASE_URL}/school/stat/",
        f"{BASE_URL}/school/commissions/",
        f"{BASE_URL}/school/helpful/",
        f"{BASE_URL}/school/map/"
    ],
    "social" :[
        f"{BASE_URL}/uk-falsification/",
        f"{BASE_URL}/districts-info/district/",
        f"{BASE_URL}/disconnections/",
        f"{BASE_URL}/gati/orders/work-type-all/"
    ]
}

TOXIC_WORDS = [
    "хуй", "хуе", "хуё", "хуя",  
    "пизд", "еба", "ебл", "ебт", 
    "бляд", "блят", "бляц",    
    "муда", "манда", "гандон",   
    "сук", "сучк",             
    "хер", "хрен", 
    "тупой", "тупиц", "тупорыл",
    "идиот", "дебил", "кретин", "имбецил", "даун",
    "урод", "ублюдок", "тварь", "мразь", "скотина",
    "лох", "лош", "чмо", "чмыр",
    "говно", "говн", "дерьм", "жоп",
    "дурак", "дура",
    "заткнись", "соси", "убью", "сдохни", "пошел на",
    "ненавижу", "бесишь",
    "Говно", "залупа", "пенис", "хер", "давалка", "хуй", "блядина"
    "Головка", "шлюха", "жопа", "член", "еблан", "петух", "Мудила"
    "Рукоблуд", "ссанина", "очко", "блядун", "вагина"
    "Сука", "ебланище", "влагалище", "пердун", "дрочила"
    "Пидор", "пизда", "туз", "малафья"
    "Гомик", "мудила", "пилотка", "манда"
    "Анус", "вагина", "путана", "педрила"
    "Шалава", "хуило", "мошонка", "елда"]

def check_toxicity(text: str) -> bool:
    """Проверка на мат."""
    for word in TOXIC_WORDS:
        if word in text.lower():
            return True
    return False


def extract_data_safe(json_response):
    """Безопасное извлечение списка данных из любого JSON."""
    if isinstance(json_response, list):
        return json_response
    if isinstance(json_response, dict):
        return json_response.get("data") or json_response.get("results") or []
    return []


def ask_agent(user_input: str, chat_history: list = None, extra_context: str = ""):
    """Helper to invoke the agent executor with optional chat history and extra context.

    - user_input: the raw text from the user
    - chat_history: list of LangChain HumanMessage/AIMessage objects
    - extra_context: string with additional context (search or parsing results) appended to input
    """
    if chat_history is None:
        chat_history = []

    # Append context to the human prompt to give the agent additional facts to use
    prompt_input = user_input
    if extra_context:
        prompt_input = f"{user_input}\n\n[CONTEXT]:\n{extra_context}"

    try:
        response = agent_executor.invoke({
            "input": prompt_input,
            "chat_history": chat_history
        })
        # If the agent returns a dictionary or dict-like output, try grabbing 'output' key
        if isinstance(response, dict):
            return response.get('output') or response.get('result') or str(response)
        return str(response)
    except Exception as e:
        return f"Ошибка при вызове AI: {e}"


def detect_category(text: str) -> list:
    """Простая категориальная детекция запроса на основе ключевых слов.

    Возвращает список возможных категорий (из API_CATALOG) в порядке релевантности.
    """
    text_lower = text.lower()
    scores = {k: 0 for k in API_CATALOG.keys()}

    # Keywords mapping
    keyword_map = {
        'documents': ['мфц', 'паспорт', 'регистрац', 'свидетельств', 'документ', 'загран', 'регистрация', 'пропис', 'прописка', 'свидетельство'],
        'pets': ['вакцинация', 'ветеринар', 'питомец', 'животн', 'собак', 'кошка', 'кролик', 'ветклиник', 'питомец', 'питомцы'],
        'health': ['поликлиник', 'врач', 'запись к врачу', 'вызов врача', 'медицин', 'здоровье', 'вакцинация', 'прививка'],
        'iparent': ['дет', 'детский', 'сад', 'школ', 'класс', 'младш', 'детс', 'приём в сад', 'учебн'],
        'social': ['соц', 'льгот', 'пособ', 'субсид', 'пенси', 'пенсия', 'поддержк', 'жкх', 'отключен', 'отключения']
    }

    # Score keywords
    for cat, keywords in keyword_map.items():
        for kw in keywords:
            if kw in text_lower:
                scores[cat] += 2

    # Score by presence of category names in the text
    for cat in API_CATALOG.keys():
        if cat in text_lower:
            scores[cat] += 3

    # Add small scoring for presence of generic tokens
    generic_map = {
        'documents': ['документы', 'мфц', 'паспорт'],
        'pets': ['питомец', 'ветеринар', 'зоопарк'],
    }
    for cat, tokens in generic_map.items():
        for t in tokens:
            if t in text_lower:
                scores[cat] += 1

    # Sort categories by descending score and filter score>0
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    ranked = [k for k, v in ranked if v > 0]

    # If nothing matched, return all categories as fallback
    if not ranked:
        return list(API_CATALOG.keys())
    return ranked

def search_city_services(query: str, category: str) -> str:
    """
    Универсальный поиск по городским сервисам.
    Args:
        query: Ключевое слово (например: 'паспорт', 'прививка', 'площадка', 'мфц').
        category: Категория ('pets', 'documents', 'health', 'social', 'iparent').
    """
    print(f"\n[TOOL LOG] 🔍 Категория: {category.upper()} | Запрос: '{query}'")
    
    urls = API_CATALOG.get(category)
    if not urls:
        return f"Категория '{category}' пока пуста или не подключена."

    results = []
    headers = {'Accept': 'application/json'}
    
    # Подготовка поиска (грубый стемминг)
    query_lower = query.lower()
    search_root = query_lower[:-1] if len(query_lower) > 4 else query_lower

    # Проход по всем URL категории
    for url in urls:
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=5)
            if response.status_code == 200:
                data = extract_data_safe(response.json())
                for item in data:
                    # Собираем весь текст объекта в одну строку
                    full_text = (
                        f"{item.get('name', '')} {item.get('title', '')} "
                        f"{item.get('address', '')} {item.get('description', '')} "
                        f"{item.get('text', '')}"
                    ).lower()
                    
                    # Ищем вхождение
                    if search_root in full_text:
                        title = item.get('name') or item.get('title') or 'Без названия'
                        address = item.get('address')
                        
                        card = f"- {title}"
                        if address:
                            card += f" (📍 {address})"
                        results.append(card)
        except Exception as e:
            print(f"[TOOL ERROR] Ошибка чтения {url}: {e}")

    # Если ничего не нашли
    if not results:
        return f"По запросу '{query}' в категории '{category}' ничего не найдено."
    
    # Логика ограничения выдачи
    total_found = len(results)
    limit = 10
    shown_results = results[:limit]
    
    output_text = f"""
[СИСТЕМНАЯ ИНФОРМАЦИЯ ДЛЯ AI]:
1. Всего в базе найдено записей: {total_found}.
2. Ты видишь только первые {limit}.
3. ЕСЛИ ПОЛЬЗОВАТЕЛЬ СПРОСИТ "ПОЧЕМУ ТАК МАЛО" ИЛИ "ПОКАЖИ ВСЕ" — НЕ ИЩИ ЗАНОВО!
   Просто объясни, что записей {total_found}, но ты показываешь топ-{limit} для удобства.
   Попроси уточнить район.

[РЕЗУЛЬТАТЫ ПОИСКА]:
""" + "\n".join(shown_results)
    
    return output_text


@tool
def search_city_services_tool(query: str, category: str) -> str:
    """LangChain tool wrapper for search_city_services implementation."""
    return search_city_services(query, category)


def parse_site_impl(config_key: str = 'gu_spb_knowledge', limit: int = 10) -> str:
    """Parse site by config name and return short summary.

    If config_key is 'all', parses all configured sites in `PARSER_CONFIGS` and returns a summary.
    """
    parser = UniversalParser()
    summaries = []
    targets = []
    if config_key == 'all':
        targets = list(PARSER_CONFIGS.keys())
    else:
        # allow using both short keys and full names (case-insensitive)
        if config_key in PARSER_CONFIGS:
            targets = [config_key]
        else:
            # try to find a matching key by substring
            for k in PARSER_CONFIGS:
                if config_key.lower() in k.lower():
                    targets.append(k)
            if not targets:
                return f"Конфиг '{config_key}' не найден"

    total_items = 0
    for tk in targets[:5]:  # avoid parsing too many at once
        cfg = PARSER_CONFIGS[tk]
        try:
            items = parser.parse_site(cfg)
            count = len(items)
            total_items += count
            # summarize titles
            top_titles = [it.get('title') or it.get('name') or 'Без названия' for it in items[:limit]]
            summaries.append(f"[{tk}] parsed {count} items; top: {', '.join(top_titles[:5])}")
        except Exception as e:
            summaries.append(f"[{tk}] parse failed: {e}")



@tool
def parse_site_tool(config_key: str = 'gu_spb_knowledge', limit: int = 10) -> str:
    """LangChain tool wrapper for `parse_site_impl` - parses content from a configured site and returns a short summary."""
    return parse_site_impl(config_key, limit)

llm = GigaChat(
    credentials=GIGACHAT_CREDENTIALS, 
    verify_ssl_certs=False,
    model="GigaChat" # не забыть про добавть
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
)

tools = [search_city_services_tool, parse_site_tool]

# Системный промпт (Личность + Инструкции)
system_prompt = """
Ты — «Городской советник» Санкт-Петербурга.

ТВОЯ СТРАТЕГИЯ:
1. Сначала посмотри в ИСТОРИЮ ДИАЛОГА. Если ответ уже был, не вызывай инструмент повторно.
2. Если нужно найти информацию, используй 'search_city_services'.
4. Если нужно обновить или получить свежий контент с веб-сайта, используй 'parse_site_tool' с параметром config_key, например 'gu_spb_knowledge' или 'gu_spb_mfc'.
3. Всегда обращай внимание на [СИСТЕМНУЮ ИНФОРМАЦИЮ] в ответе инструмента. Если там написано, что записей много, сообщи об этом пользователю.

ПРАВИЛА КАТЕГОРИЙ (для инструмента):
- 'pets': Животные (клиники, площадки, советы).
- 'documents': МФЦ, документы, справки.
- 'health': Здоровье.
- 'social': Льготы, пособия, откючения, плановые работы.
- 'iparent': Родитель (детские площадки, детские сады, кружки, учреждения).
"""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("placeholder", "{chat_history}"), # Сюда подставляется память
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"), # Сюда подставляется вызов функции
])

agent = create_tool_calling_agent(llm, tools, prompt_template)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

if __name__ == "__main__":
    print("🤖 Бот запущен! (Напиши 'exit' для выхода)")
    
    # Хранилище истории диалога
    chat_history = [] 

    while True:
        try:
            user_input = input("\nВы: ")
            if user_input.lower() in ["exit", "выход"]:
                break
            
            # Проверка на токсичность
            if check_toxicity(user_input):
                print("Бот: (Игнорирует сообщение)")
                continue
            
            # Запуск агента с историей
            response = agent_executor.invoke({
                "input": user_input,
                "chat_history": chat_history
            })
            
            bot_answer = response['output']
            print(f"Бот: {bot_answer}")
            
            # Сохраняем переписку в память
            chat_history.append(HumanMessage(content=user_input))
            chat_history.append(AIMessage(content=bot_answer))
            
            # Держим в памяти только последние 10 фраз, чтобы не перегружать токенами
            if len(chat_history) > 10:
                chat_history = chat_history[-10:]
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")