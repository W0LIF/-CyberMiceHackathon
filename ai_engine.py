import os
import requests
import urllib3
import json

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

@tool
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

tools = [search_city_services]

# Системный промпт (Личность + Инструкции)
system_prompt = """
Ты — «Городской советник» Санкт-Петербурга.

ТВОЯ СТРАТЕГИЯ:
1. Сначала посмотри в ИСТОРИЮ ДИАЛОГА. Если ответ уже был, не вызывай инструмент повторно.
2. Если нужно найти информацию, используй 'search_city_services'.
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