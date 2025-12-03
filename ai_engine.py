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
from langchain.tools import tool

# Отключаем лишний шум
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Ваши ключи
GIGACHAT_CREDENTIALS = "MDE5YWJiZTMtNjFhMi03YjQ2LWE0ZWYtZGZhMmQzYjg0OGUyOmU3OTIwZmE5LWY2MjUtNGExMy1hYmNkLWI1Y2NkNzc4N2M2NQ=="

# Инициализация
os_manager = OpenSearchManager()
llm = GigaChat(
    credentials=GIGACHAT_CREDENTIALS, 
    verify_ssl_certs=False, 
    model="GigaChat"
)

@tool
def search_city_data(query: str) -> str:
    """
    Универсальный поиск по базе данных Санкт-Петербурга.
    Ищет ВСЁ: организации (ветклиники, МФЦ, школы), адреса, законы и инструкции.
    Используй этот инструмент для ЛЮБОГО вопроса.
    """
    print(f"\n[OPENSEARCH] 🔍 Запрос: '{query}'")
    
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
        if s.get('address'): details.append(f"📍 {s.get('address')}")
        if s.get('phone'): details.append(f"📞 {s.get('phone')}")
        
        # Обрезаем описание, чтобы не перегружать контекст
        content = s.get('content', '')[:150].replace("\n", " ")
        if content: details.append(f"📝 {content}...")
        
        if s.get('link') and s.get('link') != "#": 
            details.append(f"🔗 {s.get('link')}")
        
        output += f"{i}. {title} ({category})\n   " + "\n   ".join(details) + "\n\n"
        
    return output

# У нас теперь всего ОДИН мощный инструмент
tools = [search_city_data]

system_prompt = """
Ты — «Городской советник» Санкт-Петербурга.
Твоя задача — отвечать на вопросы жителей, используя ТОЛЬКО локальную базу данных.

ТВОЯ СТРАТЕГИЯ:
1. Любой вопрос про город (адреса, телефоны, законы, "где найти") -> вызывай `search_city_data`.
2. Передавай в поиск ключевые слова. 
   - Если ищут "ветклиники в Адмиралтейском" -> ищи "ветклиника Адмиралтейский".
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

if __name__ == "__main__":
    print("🤖 Бот запущен! (Работает только с базой OpenSearch)")
    chat_history = [] 

    while True:
        try:
            user_input = input("\nВы: ")
            if user_input.lower() in ["exit", "выход"]: break
            
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