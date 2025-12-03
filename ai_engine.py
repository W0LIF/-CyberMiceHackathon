import os
import requests
import urllib3
import json

# === ИМПОРТЫ ПРОЕКТА ===
from spb_bot_opensearch.opensearch_manager import OpenSearchManager

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === ИМПОРТЫ LANGCHAIN ===
from langchain_core.messages import AIMessage, HumanMessage
from langchain_gigachat.chat_models import GigaChat
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool

# === КОНФИГУРАЦИЯ ===
GIGACHAT_CREDENTIALS = "MDE5YWJiZTMtNjFhMi03YjQ2LWE0ZWYtZGZhMmQzYjg0OGUyOmU3OTIwZmE5LWY2MjUtNGExMy1hYmNkLWI1Y2NkNzc4N2M2NQ=="
BASE_URL = "https://yazzh.gate.petersburg.ru"

# ======================================================================================
# 🛠️ ЗОНА НАСТРОЙКИ API (ЗАПОЛНИ ЭТО)
# ======================================================================================
# district_key: как называется параметр района в URL? (например "district", "area_id"). 
#               Если не знаешь или API не умеет фильтровать — ставь None.
# keyword_key:  как называется параметр текстового поиска? (например "q", "search", "text").
#               Если не знаешь — ставь None.
# static_params: параметры, которые отправляются ВСЕГДА (например {"limit": 100}).

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
# ======================================================================================

TOXIC_WORDS = ["хуй", "пизд", "бляд", "еба", "говно", "муда", "сук"] 

def check_toxicity(text: str) -> bool:
    for word in TOXIC_WORDS:
        if word in text.lower(): return True
    return False

def extract_data_safe(json_response):
    if isinstance(json_response, list): return json_response
    if isinstance(json_response, dict): return json_response.get("data") or json_response.get("results") or []
    return []

# === ИНИЦИАЛИЗАЦИЯ ===
os_manager = OpenSearchManager()

llm = GigaChat(
    credentials=GIGACHAT_CREDENTIALS, 
    verify_ssl_certs=False,
    model="GigaChat" 
)

# === ИНСТРУМЕНТЫ (TOOLS) ===

@tool
def search_api_catalog(category: str, district: str = "", keyword: str = "") -> str:
    """
    Ищет в городском API, подставляя параметры в URL, если они настроены.
    
    Args:
        category: СТРОГО одна из: 'pets', 'documents', 'health', 'social', 'iparent'.
        query: отправляй пустой запрос.
    """
    print(f"\n[API] 📂 Категория: {category.upper()} | Район: '{district}' | Ключ: '{keyword}'")
    
    endpoints = API_CATALOG.get(category)
    if not endpoints: return f"Ошибка: Категория '{category}' не настроена."

    results = []
    headers = {'Accept': 'application/json'}
    
    # Подготовка корней слов для Python-фильтрации (на случай, если API не умеет фильтровать)
    district_root = ""
    if district:
        clean = district.strip().lower().split()[0]
        if len(clean) > 4: district_root = clean[:-1]
        else: district_root = clean

    for entry in endpoints:
        url = entry["url"]
        config = entry["params_config"]
        
        # 1. ФОРМИРУЕМ ПАРАМЕТРЫ ЗАПРОСА (GET params)
        params = config.get("static_params", {}).copy()
        
        # Если в конфиге задан ключ для района, добавляем его
        if district and config["district_key"]:
            params[config["district_key"]] = district
            
        # Если в конфиге задан ключ для поиска, добавляем его
        if keyword and config["keyword_key"]:
            params[config["keyword_key"]] = keyword

        try:
            # print(f"[DEBUG] GET {url} params={params}") 
            # Отправляем запрос с параметрами (или пустой, если params пуст)
            response = requests.get(url, params=params, headers=headers, verify=False, timeout=5)
            
            if response.status_code == 200:
                data = extract_data_safe(response.json())
                
                for item in data:
                    actual_item = item
                    if 'place' in item and isinstance(item['place'], dict):
                        actual_item = item['place']
                    
                    # 2. ДОПОЛНИТЕЛЬНАЯ ФИЛЬТРАЦИЯ (PYTHON)
                    # Даже если мы отправили параметры, API мог вернуть мусор.
                    # Или если параметры были None, мы скачали всё.
                    # Поэтому проверяем район еще раз здесь.
                    
                    def get_all_text(d):
                        t = ""
                        for v in d.values():
                            if isinstance(v, dict): t += get_all_text(v)
                            elif isinstance(v, list): t += " ".join([str(x) for x in v])
                            elif v: t += str(v) + " "
                        return t

                    full_text = get_all_text(actual_item).lower()
                    
                    # Если параметр района НЕ был отправлен на сервер (None), 
                    # то фильтруем руками здесь.
                    if district_root and (config["district_key"] is None):
                         if district_root not in full_text:
                            continue
                    
                    # Если параметр ключа НЕ был отправлен на сервер (None),
                    # то фильтруем руками здесь.
                    if keyword and (config["keyword_key"] is None):
                        if keyword.lower() not in full_text:
                            continue

                    # Сборка карточки
                    title = (actual_item.get('name') or actual_item.get('title') or 'Без названия')
                    address = (actual_item.get('address') or actual_item.get('location') or '')
                    if isinstance(address, dict): address = str(address.get('address', ''))
                    
                    card = f"- {title}"
                    if address: card += f" (📍 {address})"
                    if actual_item.get('phone'): card += f" 📞 {actual_item.get('phone')}"
                    
                    results.append(card)
        except Exception:
            pass

    results = list(set([r for r in results if r]))

    if not results:
        return f"По запросу ничего не найдено в категории '{category}'."
    
    limit = 10
    output = "\n".join(results[:limit])
    if len(results) > limit:
        return f"Найдено {len(results)} записей. Вот первые {limit}:\n{output}"
    
    return output

@tool
def search_knowledge_base(query: str) -> str:
    """Ищет инструкции, законы и статьи (ТЕКСТ) в базе знаний."""
    print(f"\n[OPENSEARCH] 📚 Ищу инструкции: '{query}'")
    results = os_manager.search(query, size=3)
    if not results: return "В базе знаний ничего не найдено."
    
    output = ""
    for i, hit in enumerate(results, 1):
        s = hit['_source']
        output += f"{i}. {s.get('title')}: {s.get('content')[:200]}...\n"
    return output

# Список инструментов
tools = [search_api_catalog, search_knowledge_base]

# === НАСТРОЙКА АГЕНТА ===

system_prompt = """
Ты — «Городской советник» Санкт-Петербурга.

ТВОЯ ЗАДАЧА — ВЫБРАТЬ ИНСТРУМЕНТ И ЗАПОЛНИТЬ ПАРАМЕТРЫ.

1. Если вопрос про **АДРЕСА, ОРГАНИЗАЦИИ** ("Где?", "Куда пойти?", "Адрес"):
   -> Используй `search_api_catalog`.
   -> отпраляй пустой запрос.
   -> находи из ответа нужное пользователю.

2. Если вопрос про **ИНСТРУКЦИИ, ЗАКОНЫ** ("Как?", "Что нужно?"):
   -> Используй `search_knowledge_base`.

Пример:
User: "Где терапевт в Адмиралтейском?"
AI: search_api_catalog(category="health", district="адмиралтейский", keyword="терапевт")
"""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt_template)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

if __name__ == "__main__":
    print("🤖 Бот запущен! (Режим: Шаблоны параметров)")
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