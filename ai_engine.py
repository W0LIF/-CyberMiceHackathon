import os
import urllib3
import logging

from spb_bot_opensearch.opensearch_manager import OpenSearchManager

from langchain_core.messages import AIMessage, HumanMessage
from langchain_gigachat.chat_models import GigaChat
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.tools import tool

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GIGACHAT_CREDENTIALS = "MDE5YWJiZTMtNjFhMi03YjQ2LWE0ZWYtZGZhMmQzYjg0OGUyOmU3OTIwZmE5LWY2MjUtNGExMy1hYmNkLWI1Y2NkNzc4N2M2NQ=="

os_manager = OpenSearchManager()

try:
    was_updated = os_manager.ensure_data_loaded()
    if was_updated: print("[ai_engine] Данные обновлены")
except Exception as e:
    print(f"[ai_engine] Ошибка инициализации: {e}")

llm = GigaChat(
    credentials=GIGACHAT_CREDENTIALS, 
    verify_ssl_certs=False, 
    model="GigaChat",
    temperature=0.1
)

# === МОДЕРАЦИЯ ===
validation_template = """
Ты — модератор. Проверь сообщение на токсичность/мат.
Если токсично — ответь BLOCK. Иначе — PASS.
Сообщение: "{text}"
Ответ:
"""
validation_chain = ChatPromptTemplate.from_template(validation_template) | llm | StrOutputParser()

# === ИНСТРУМЕНТ 1: ДЛЯ АДРЕСОВ (Школы, МФЦ, Клиники) ===

@tool
def find_places(query: str, district: str = None) -> str:
    """
    Ищет ОРГАНИЗАЦИИ и АДРЕСА: школы, МФЦ, ветклиники, больницы.
    Аргументы:
    - query: название или тип (например "школа", "МФЦ", "ветклиника").
    - district: Район (если указан). Например: "Адмиралтейский".
    """
    raw_query = query.lower().strip()
    
    # === 1. УМНАЯ НОРМАЛИЗАЦИЯ ЗАПРОСА ===
    # Помогаем базе данных найти правильные слова
    search_query = raw_query
    
    if "вет" in raw_query or "животн" in raw_query:
        search_query = "ветеринарная клиника" # Ищем точную фразу, которая есть в базе
    elif "мфц" in raw_query or "документ" in raw_query:
        search_query = "мфц"
    elif "школ" in raw_query:
        search_query = "школа"
    elif "сад" in raw_query:
        search_query = "детский сад"
    elif "больниц" in raw_query or "поликлин" in raw_query:
        search_query = "поликлиника"

    print(f"\n[TOOL: PLACES] Запрос юзера: '{raw_query}' -> Ищем в базе: '{search_query}' | Район: '{district}'")
    
    # 2. Выгружаем МНОГО данных (size=1000), чтобы не потерять объекты
    raw_results = os_manager.search(search_query, size=1000)
    
    final_results = []

    # 3. ЖЕСТКАЯ ФИЛЬТРАЦИЯ ПО РАЙОНУ (PYTHON)
    if district:
        # "Адмиралтейский" -> "адмиралтейск"
        dist_root = district.lower().strip()
        if len(dist_root) > 4: dist_root = dist_root[:-2]

        for hit in raw_results:
            s = hit['_source']
            # Собираем текст для проверки района (Заголовок + Адрес + Поле District)
            # В файлах pets района может не быть в поле district, но он есть в адресе!
            check_text = (str(s.get('district', '')) + " " + s.get('title', '') + " " + s.get('address', '')).lower()
            
            if dist_root in check_text:
                final_results.append(hit)
    else:
        final_results = raw_results

    if not final_results:
        return f"Не найдено организаций по запросу '{query}' в районе '{district}'."

    # 4. ФОРМАТИРОВАНИЕ
    display_results = final_results[:15]
    
    output = f"[НАЙДЕНО {len(final_results)} МЕСТ (Показано {len(display_results)})]:\n"
    for i, hit in enumerate(display_results, 1):
        s = hit['_source']
        title = s.get('title', 'Без названия')
        addr = s.get('address', 'Адрес не указан')
        phone = s.get('phone', '')
        
        output += f"{i}. {title}\n"
        output += f"   📍 {addr}\n"
        if phone: output += f"   📞 {phone}\n"
        
        # Если это ветклиника, часто полезно знать профиль или часы работы (если есть в базе)
        if s.get('working_hours'):
             output += f"   🕒 {s.get('working_hours')}\n"

        output += "\n"

    return output


# === ИНСТРУМЕНТ 2: ДЛЯ ИНФОРМАЦИИ (Законы, Льготы) ===

@tool
def search_knowledge_base(query: str) -> str:
    """
    Ищет ИНФОРМАЦИЮ: законы, льготы, пособия, правила, инструкции ("как получить", "что делать").
    НЕ используй для поиска адресов.
    """
    print(f"\n[TOOL: KNOWLEDGE] Ищем информацию: '{query}'")
    
    results = os_manager.search(query, size=5)
    
    if not results:
        return "В базе знаний нет информации по этому вопросу."
    
    output = f"[НАЙДЕНО {len(results)} СТАТЕЙ]:\n"
    for i, hit in enumerate(results, 1):
        s = hit['_source']
        title = s.get('title', 'Без названия')
        # Агрессивно собираем текст
        content = str(s.get('content') or s.get('description') or s.get('text') or "")
        clean_content = " ".join(content.split())[:300]
        link = s.get('link', '')
        
        output += f"{i}. {title}\n"
        if clean_content: output += f"   Инфо: {clean_content}...\n"
        if link and link != "#": output += f"   Ссылка: {link}\n"
        output += "\n"
        
    return output

# Список инструментов
tools = [find_places, search_knowledge_base]

# === ПРОМПТ ===

system_prompt = """
Ты — «Городской советник» Санкт-Петербурга.

ТВОЯ СТРАТЕГИЯ ВЫБОРА:
1. 🏢 Если спрашивают **"ГДЕ находится?", "Адреса...", "Школы/МФЦ в районе..."**:
   -> Используй `find_places`.
   - Обязательно выдели название района, если оно есть (например "Адмиралтейский").

2. 📜 Если спрашивают **"КАК получить?", "Какие льготы?", "Закон о..."**:
   -> Используй `search_knowledge_base`.

3. Отвечай вежливо, используй найденные данные. Если адресов много, выведи их списком.
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
    print("🤖 Бот запущен! (Гибридный режим: Адреса + Знания)")
    chat_history = [] 

    while True:
        try:
            user_input = input("\nВы: ")
            if user_input.lower() in ["exit", "выход"]: break
            
            val = validation_chain.invoke({"text": user_input})
            if "BLOCK" in val.strip().upper():
                print("⛔ Соблюдайте приличия.")
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