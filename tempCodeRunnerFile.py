import os
import requests
import urllib3
import json

# === ИМПОРТЫ ПРОЕКТА ===
# Импортируем менеджер OpenSearch
from spb_bot_opensearch.opensearch_manager import OpenSearchManager
from parsing.universal_parser import UniversalParser, CONFIGURATIONS as PARSER_CONFIGS

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) # Отключение предупреждений SSL

# === ИМПОРТЫ LANGCHAIN ===
from langchain_core.messages import AIMessage, HumanMessage
from langchain_gigachat.chat_models import GigaChat
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool

# === КОНФИГУРАЦИЯ ===
GIGACHAT_CREDENTIALS = "MDE5YWJiZTMtNjFhMi03YjQ2LWE0ZWYtZGZhMmQzYjg0OGUyOmU3OTIwZmE5LWY2MjUtNGExMy1hYmNkLWI1Y2NkNzc4N2M2NQ=="
BASE_URL = "https://yazzh.gate.petersburg.ru"

API_CATALOG = {
    "pets": [
        f"{BASE_URL}/mypets/all-category/",
        f"{BASE_URL}/mypets/posts/",
        f"{BASE_URL}/mypets/recommendations/",
        f"{BASE_URL}/mypets/animal-breeds/",
    ],
    "documents": [f"{BASE_URL}/mfc/all/"],
    "health": [f"{BASE_URL}/polyclinics/"],
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
    "social": [
        f"{BASE_URL}/uk-falsification/",
        f"{BASE_URL}/districts-info/district/",
        f"{BASE_URL}/disconnections/",
        f"{BASE_URL}/gati/orders/work-type-all/"
    ]
}

TOXIC_WORDS = [
    "хуй", "хуе", "хуё", "хуя", "пизд", "еба", "ебл", "ебт", 
    "бляд", "блят", "бляц", "муда", "манда", "гандон", "сук", "сучк",             
    "хер", "хрен", "тупой", "тупиц", "тупорыл", "идиот", "дебил", 
    "кретин", "имбецил", "даун", "урод", "ублюдок", "тварь", "мразь", 
    "скотина", "лох", "лош", "чмо", "чмыр", "говно", "говн", "дерьм", 
    "жоп", "дурак", "дура", "заткнись", "соси", "убью", "сдохни", 
    "пошел на", "ненавижу", "бесишь", "залупа", "пенис", "давалка", 
    "блядина", "шлюха", "член", "еблан", "петух", "мудила", "рукоблуд", 
    "ссанина", "очко", "блядун", "вагина", "ебланище", "влагалище", 
    "пердун", "дрочила", "пидор", "пизда", "туз", "малафья", "гомик", 
    "пилотка", "анус", "путана", "педрила", "шалава", "хуило", "мошонка", "елда"
]

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

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

# === ЛОГИКА ПОИСКА (API) ===
# Используем улучшенную версию с рекурсией и корнями слов

def search_city_services(query: str, category: str) -> str:
    """Универсальный поиск по городским сервисам (API)."""
    print(f"\n[TOOL LOG] 🔍 Категория: {category.upper()} | Запрос: '{query}'")
    
    urls = API_CATALOG.get(category)
    if not urls:
        return f"Категория '{category}' пока пуста или не подключена."

    results = []
    headers = {'Accept': 'application/json'}
    
    # Разбиваем запрос на корни слов (для нечеткого поиска)
    query_roots = []
    for word in query.lower().split():
        clean_word = word.strip(".,?!")
        if len(clean_word) > 4:
            query_roots.append(clean_word[:-1]) 
        elif len(clean_word) > 2:
            query_roots.append(clean_word)

    for url in urls:
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=5)
            if response.status_code == 200:
                data = extract_data_safe(response.json())
                
                for item in data:
                    # 1. Распаковка вложенных данных (для mypets)
                    actual_item = item
                    if 'place' in item and isinstance(item['place'], dict):
                        actual_item = item['place']
                    
                    # 2. Рекурсивный сбор всего текста
                    def get_all_values(d):
                        text = ""
                        for v in d.values():
                            if isinstance(v, dict): text += get_all_values(v)
                            elif isinstance(v, list): text += " ".join([str(x) for x in v])
                            elif v: text += str(v) + " "
                        return text

                    full_text = get_all_values(actual_item).lower()
                    
                    # 3. Поиск совпадений
                    if any(root in full_text for root in query_roots):
                        title = (actual_item.get('name') or actual_item.get('title') or 'Без названия')
                        address = (actual_item.get('address') or actual_item.get('location') or '')
                        if isinstance(address, dict): address = str(address.get('address', ''))
                            
                        card = f"- {title}"
                        if address: card += f" (📍 {address})"
                        if actual_item.get('phone'): card += f" 📞 {actual_item.get('phone')}"
                            
                        results.append(card)
        except Exception as e:
            print(f"[TOOL ERROR] Ошибка чтения {url}: {e}")

    results = list(set([r for r in results if r])) # Удаляем дубли

    if not results:
        return f"По запросу '{query}' в категории '{category}' ничего не найдено."
    
    # Лимит выдачи
    limit = 15
    return f"[СИСТЕМНАЯ ИНФОРМАЦИЯ]: Найдено {len(results)}. Топ-{limit}:\n" + "\n".join(results[:limit])


# === ЛОГИКА ПАРСИНГА САЙТОВ ===

def parse_site_impl(config_key: str = 'gu_spb_knowledge', limit: int = 10) -> str:
    """Реализация парсинга."""
    parser = UniversalParser()
    if config_key not in PARSER_CONFIGS:
        return f"ОШИБКА: Конфиг '{config_key}' не существует. Доступные: {', '.join(PARSER_CONFIGS.keys())}"

    try:
        items = parser.parse_site(PARSER_CONFIGS[config_key])
        top_titles = [it.get('title') or it.get('name') or 'Без названия' for it in items[:limit]]
        return f"[{config_key}] получено {len(items)} записей. Примеры: {', '.join(top_titles[:5])}"
    except Exception as e:
        return f"Ошибка парсинга: {e}"

# === ИНИЦИАЛИЗАЦИЯ ===

# 1. OpenSearch
os_manager = OpenSearchManager()

# 2. GigaChat
llm = GigaChat(
    credentials=GIGACHAT_CREDENTIALS, 
    verify_ssl_certs=False,
    model="GigaChat" 
)

# === ОПРЕДЕЛЕНИЕ ИНСТРУМЕНТОВ (TOOLS) ===

@tool
def search_city_services_tool(query: str, category: str) -> str:
    """
    Ищет услуги через городское API.
    Категории (category): 'pets', 'documents', 'health', 'social', 'iparent'.
    """
    return search_city_services(query, category)

# --- Инструмент OpenSearch ---
@tool
def search_local_database(query: str) -> str:
    """
    Ищет информацию во внутренней базе знаний (OpenSearch).
    Используй этот инструмент для поиска документов, законов и справочной информации.
    """
    print(f"\n[OPENSEARCH] 🔍 Ищу в базе: '{query}'")
    results = os_manager.search(query, size=3)
    
    if not results:
        return "В локальной базе знаний ничего не найдено."
    
    output = "[РЕЗУЛЬТАТЫ ИЗ БАЗЫ ЗНАНИЙ]:\n"
    for i, hit in enumerate(results, 1):
        source = hit['_source']
        title = source.get('title', 'Без заголовка')
        content = source.get('content', '')[:400]
        link = source.get('link', '#')
        output += f"{i}. {title} (Категория: {source.get('category')})\n   Текст: {content}...\n   Ссылка: {link}\n\n"
    return output

# --- Инструмент Парсинга (с фиксом docstring) ---
AVAILABLE_CONFIGS = ", ".join(PARSER_CONFIGS.keys())

def parse_site_func(config_key: str = 'gu_spb_knowledge', limit: int = 10) -> str:
    return parse_site_impl(config_key, limit)

# Вручную задаем описание, чтобы LangChain не ругался
parse_site_func.__doc__ = f"""
Парсит сайт. Использовать ТОЛЬКО ключи: {AVAILABLE_CONFIGS}.
Если ключа нет - не вызывай.
"""
parse_site_tool = tool(parse_site_func)

# Список инструментов
tools = [search_local_database, search_city_services_tool, parse_site_tool]

# === НАСТРОЙКА АГЕНТА ===

system_prompt = """
Ты — «Городской советник» Санкт-Петербурга.

ТВОЯ СТРАТЕГИЯ:
1. Сначала посмотри в ИСТОРИЮ ДИАЛОГА.
2. Первым делом ищи в API ('search_city_services_tool').
3. Если там пусто — ищи в базе знаний ('search_local_database').
4. Если нигде нет — честно скажи об этом.

ПРАВИЛА КАТЕГОРИЙ (для API):
- 'pets': ВЕТЕРИНАРЫ, животные, площадки.
- 'health': ЧЕЛОВЕЧЕСКИЕ врачи и поликлиники.
- 'documents': МФЦ, паспорта.
- 'social': ЖКХ, льготы.
- 'iparent': Школы, сады.

ПРАВИЛА ЗАПРОСА:
- НЕ запрашивай ближайшие и тд только название района
"""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt_template)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# === ЗАПУСК ===

if __name__ == "__main__":
    print("🤖 Бот запущен! (Напиши 'exit' для выхода)")
    chat_history = [] 

    while True:
        try:
            user_input = input("\nВы: ")
            if user_input.lower() in ["exit", "выход"]: break
            
            if check_toxicity(user_input):
                print("Бот: (Игнорирует сообщение)")
                continue
            
            response = agent_executor.invoke({
                "input": user_input,
                "chat_history": chat_history
            })
            
            bot_answer = response['output']
            print(f"Бот: {bot_answer}")
            
            chat_history.append(HumanMessage(content=user_input))
            chat_history.append(AIMessage(content=bot_answer))
            if len(chat_history) > 10: chat_history = chat_history[-10:]
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")