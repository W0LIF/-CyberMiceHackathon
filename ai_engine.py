import os
import urllib3
import logging
# Импортируем наш менеджер
from spb_bot_opensearch.opensearch_manager import OpenSearchManager

# Импорты LangChain
from langchain_core.messages import AIMessage, HumanMessage
from langchain_gigachat.chat_models import GigaChat
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.tools import tool

# Отключаем лишний шум
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Ваши ключи
GIGACHAT_CREDENTIALS = "MDE5YWJiZTMtNjFhMi03YjQ2LWE0ZWYtZGZhMmQzYjg0OGUyOmU3OTIwZmE5LWY2MjUtNGExMy1hYmNkLWI1Y2NkNzc4N2M2NQ=="

# Инициализация
os_manager = OpenSearchManager()

# Проверяем и загружаем данные при старте
try:
    was_updated = os_manager.ensure_data_loaded()
    if was_updated:
        print("[ai_engine] Данные загружены/обновлены в OpenSearch")
except Exception as e:
    print(f"[ai_engine] Ошибка при инициализации данных: {e}")

llm = GigaChat(
    credentials=GIGACHAT_CREDENTIALS, 
    verify_ssl_certs=False, 
    model="GigaChat"
)

validation_template = """
Ты — строгий модератор чата. Твоя задача — проверить сообщение пользователя.
Если сообщение содержит нецензурную лексику, прямые оскорбления, угрозы или явную токсичность — ответь одним словом: BLOCK.
Если сообщение корректное (даже если это жалоба или спор) — ответь одним словом: PASS.

Сообщение пользователя: "{text}"

Ответ (только BLOCK или PASS):
"""
validation_prompt = ChatPromptTemplate.from_template(validation_template)
validation_chain = validation_prompt | llm | StrOutputParser()


@tool
def school(query: str, district: str = None) -> str:
    """
    Ищет школы.
    Аргументы:
    - query: запрос (например "математическая" или просто "школы")
    - district: Район города. ВАЖНО: Должен быть в Именительном падеже с большой буквы.
      Пример: "в адмиралтейском" -> пиши "Адмиралтейский". 
      Пример: "школы василеостровского района" -> пиши "Василеостровский".
    """
    target_file = "api_iparent_2.json"
    
    # Если query слишком общий, очищаем его, чтобы сработал match_all
    if query.lower().strip() in ["школы", "школа", "гимназии", "лицеи"]:
        query = ""

    print(f"\n[TOOL: SCHOOL] Поиск: '{query}' | Район: '{district}'")
    
    results = os_manager.search(query, source=target_file, district=district, size=5)
    
    if not results:
        return f"В базе (файл {target_file}) по запросу '{query}' в районе '{district}' ничего не найдено. Проверьте правильность названия района."
    
    output = f"[НАЙДЕНО {len(results)} ШКОЛ (Район: {district})]:\n"
    for i, hit in enumerate(results, 1):
        s = hit['_source']
        output += f"{i}. {s.get('title')} ({s.get('kind')})\n"
        output += f"   Адрес: {s.get('address')}\n"
        if s.get('profile'): 
            output += f"   Профиль: {', '.join(s.get('profile'))}\n"
        output += "\n"
        
    return output

@tool
def mfc(query: str) -> str:
    """
    Поиск адресов мфц
    Выбор файла: api_documents_0.json
    Что искать в файле: 
        
    """
    print(f"\n[OPENSEARCH] Запрос: '{query}'")
    
    # Ищем в базе (заголовки, контент, адреса)
    results = os_manager.search(query, size=7)
    
    if not results:
        return "К сожалению, в базе данных ничего не найдено по этому запросу."
    
    output = f"[НАЙДЕНО {len(results)} ОБЪЕКТОВ]:\n"
    for i, hit in enumerate(results, 1):
        s = hit['_source']
        title = s.get('title', 'Без названия')
        category = s.get('category', 'Разное')
        
        # Собираем детали
        details = []
        if s.get('address'): details.append(f"Адрес: {s.get('address')}")
        if s.get('phone'): details.append(f"Телефон: {s.get('phone')}")
        
        # Обрезаем описание, чтобы не перегружать контекст
        content = s.get('content', '')[:150].replace("\n", " ")
        if content: details.append(f"Описание: {content}...")
        
        if s.get('link') and s.get('link') != "#": 
            details.append(f"Ссылка: {s.get('link')}")
        
        output += f"{i}. {title} ({category})\n   " + "\n   ".join(details) + "\n\n"
        
    return output

tools = [mfc, school]

system_prompt = """
Ты — «Городской советник» Санкт-Петербурга.
Твоя задача — отвечать на вопросы жителей, используя ТОЛЬКО локальную базу данных.

ТВОЯ СТРАТЕГИЯ:
1. Любой вопрос про мфц -> вызывай mfc.
2. Любой вопрос про школы -> вызывай school.
2. Передавай в поиск ключевые слова. 
   - Если ищут "ветклиники в Адмиралтейском" -> ищи "Адмиралтейский".
   - Если ищут "паспорт" -> ищи "как получить паспорт".
3. В ответе инструмента ты получишь список объектов. Сформируй из них вежливый ответ.
4. Если объектов много, перечисли их списком с адресами.
"""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt_template)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

def ask_agent(user_input, chat_history=None, extra_context=""):
    """
    Функция для отправки вопроса агенту с контекстом
    """
    if chat_history is None:
        chat_history = []
    
    # Добавляем контекст к вопросу если он есть
    if extra_context:
        full_input = f"{extra_context}\n\nВопрос: {user_input}"
    else:
        full_input = user_input
    
    try:
        response = agent_executor.invoke({
            "input": full_input,
            "chat_history": chat_history
        })
        return response.get('output', 'Нет ответа')
    except Exception as e:
        print(f"[ai_engine] Ошибка при вызове агента: {e}")
        return f"Произошла ошибка при обработке запроса: {e}"

if __name__ == "__main__":
    print("Бот запущен!")
    chat_history = [] 

    while True:
        try:
            user_input = input("\nВы: ")
            if user_input.lower() in ["exit", "выход"]: break
            validation_result = validation_chain.invoke({"text": user_input})
            if "BLOCK" in validation_result.strip().upper():
                print("⛔ Бот: Пожалуйста, соблюдайте нормы приличия. Я не отвечаю на грубость.")
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
            print(f"Ошибка: {e}")