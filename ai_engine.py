import os
import urllib3
import logging

from spb_bot_opensearch.opensearch_manager import OpenSearchManager
from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage
from langchain_gigachat.chat_models import GigaChat
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.tools import tool

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GIGACHAT_CREDENTIALS = "MDE5YWUxMWUtZmU1OC03N2EyLTkyNDEtYmQ0ODg0ZDAyNGVlOjRhOTk5NTU0LWM2NTktNDk1ZC05OTdmLWYwMmZhNWJiZWNiYQ=="

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
def search_city_data(query: str, district: Optional[str] = None) -> str:
    """
    Универсальный поиск по базе данных Санкт-Петербурга.
    Ищет ВСЁ: организации (ветклиники, МФЦ, школы), адреса, законы и инструкции.
    
    Аргументы:
    - query: Ваш запрос (например "ветклиника", "как получить паспорт", "школа").
    - district: Район (если указан). Например: "Адмиралтейский".
    """
    raw_query = query.lower().strip()
    
    # === 1. УМНАЯ НОРМАЛИЗАЦИЯ (для поиска мест) ===
    search_query = raw_query
    
    # Если ищут места, подменяем на точные термины базы
    if "вет" in raw_query or "животн" in raw_query:
        search_query = "ветеринарная клиника"
    elif "мфц" in raw_query or "документ" in raw_query:
        search_query = "мфц"
    elif "школ" in raw_query:
        search_query = "школа"
    elif "сад" in raw_query and "дет" in raw_query:
        search_query = "детский сад"
    elif "больниц" in raw_query or "поликлин" in raw_query:
        search_query = "поликлиника"
    
    print(f"\n[TOOL: UNIVERSAL] Запрос: '{raw_query}' -> Ищем: '{search_query}' | Район: '{district}'")
    
    # 2. ЗАПРАШИВАЕМ МАКСИМУМ (size=1000)
    # Ищем везде (source=None), первичный фильтр района отключен (district=None)
    raw_results = os_manager.search(search_query, size=1000)
    
    if not raw_results:
        return f"К сожалению, в базе данных ничего не найдено по запросу '{query}'."

    final_results = []

    # 3. ФИЛЬТРАЦИЯ ПО РАЙОНУ (PYTHON)
    if district:
        # "Адмиралтейский" -> "адмиралтейск"
        dist_root = district.lower().strip()
        if len(dist_root) > 4: dist_root = dist_root[:-2]

        for hit in raw_results:
            s = hit['_source']
            # Собираем ВЕСЬ текст для проверки района
            # (Заголовок + Адрес + Район + Контент)
            check_text = (
                str(s.get('district', '')) + " " + 
                s.get('title', '') + " " + 
                s.get('address', '') + " " + 
                str(s.get('content', ''))
            ).lower()
            
            if dist_root in check_text:
                final_results.append(hit)
    else:
        final_results = raw_results

    if not final_results:
        return f"Ничего не найдено по запросу '{query}' в районе '{district}'."

    # 4. ФОРМИРОВАНИЕ УНИВЕРСАЛЬНОГО ОТВЕТА
    # Берем топ-15, чтобы влезло в контекст
    display_results = final_results[:15]
    
    output = f"[НАЙДЕНО {len(final_results)} ОБЪЕКТОВ (Показано {len(display_results)})]:\n"
    
    for i, hit in enumerate(display_results, 1):
        s = hit['_source']
        
        # Основные поля
        title = s.get('title', 'Без названия')
        category = s.get('category', 'Общее')
        address = s.get('address', '')
        phone = s.get('phone', '')
        link = s.get('link', '')
        if link == "#": link = ""
        
        # Сбор контента (для статей/законов)
        text_parts = []
        if s.get('content'): text_parts.append(str(s.get('content')))
        if s.get('description'): text_parts.append(str(s.get('description')))
        if s.get('text'): text_parts.append(str(s.get('text')))
        full_text = " ".join(text_parts)
        clean_text = " ".join(full_text.split())

        # ВЫВОД КАРТОЧКИ
        output += f"{i}. {title} ({category})\n"
        
        # Если это место (есть адрес/телефон)
        if address: output += f"   📍 {address}\n"
        if phone: output += f"   📞 {phone}\n"
        
        # Если это статья (есть текст)
        if len(clean_text) > 10:
            preview = clean_text[:300] + "..." if len(clean_text) > 300 else clean_text
            output += f"   ℹ️ {preview}\n"
            
        # Ссылка обязательна
        if link: output += f"   🔗 {link}\n"
        
        # Доп. инфо для школ/клиник
        if s.get('profile'): output += f"   Профиль: {', '.join(s.get('profile'))}\n"
        if s.get('working_hours'): output += f"   Время: {s.get('working_hours')}\n"
            
        output += "\n"
        
    return output

# Список инструментов
tools = [search_city_data]

# === ПРОМПТ ===

system_prompt = """
Ты — «Городской советник» Санкт-Петербурга.
Твоя задача — отвечать на вопросы жителей, используя ТОЛЬКО локальную базу данных.

ТВОЯ СТРАТЕГИЯ:
1. Для ЛЮБОГО вопроса (адреса, законы, льготы) используй инструмент `search_city_data`.
2. Если в вопросе упомянут район — ОБЯЗАТЕЛЬНО передавай его в параметр `district`.
   - Пример: "ветклиники в Адмиралтейском" -> query="ветклиники", district="Адмиралтейский".
3. Форматируй ответ красиво:
   - Используй нумерованный список.
   - Если есть адрес — пиши его.
   - Если есть ссылка — ОБЯЗАТЕЛЬНО укажи её.
   - НЕ используй "**" и "#".

Если ничего не найдено — честно скажи об этом.
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