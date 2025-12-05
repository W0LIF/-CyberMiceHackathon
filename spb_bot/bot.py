from email import message
import telebot
from telebot import types
import sys
import os

# Ensure project root is on sys.path so imports like `parsing` and `ai_engine` work
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
import requests
import json
import os
from submenu import*
from parsing.universal_parser import UniversalParser, CONFIGURATIONS
import ai_engine as ai_engine
from ai_engine import ask_agent
from spb_bot_opensearch.opensearch_manager import OpenSearchManager
from langchain_core.messages import HumanMessage, AIMessage

# Инициализируем OpenSearch менеджер
os_manager = OpenSearchManager()
TOKEN = "8482065670:AAHcPeR6v20gFlgQCtfYz3uxfZY3QG4CSGo"
bot = telebot.TeleBot(TOKEN)
user_histories = {}

# Optionally start background parser if environment set
if os.getenv('START_PARSER_BACKGROUND', 'false').lower() in ('1', 'true', 'yes'):
    try:
        from parsing.background_parser import start_background_parsing
        interval_seconds = int(os.getenv('PARSER_INTERVAL_SECONDS', '3600'))
        start_background_parsing(interval_seconds=interval_seconds)
        print('[bot] Background parsing thread started')
    except Exception as e:
        print(f'[bot] Failed to start background parser: {e}')

def create_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton("🏛️ Госуслуги")
    button2 = types.KeyboardButton("💰 Соцподдержка")
    button3 = types.KeyboardButton("🚇 Транспорт")
    button4 = types.KeyboardButton("🎭 Мероприятия")
    button5 = types.KeyboardButton("❓ FAQ")
    button6 = types.KeyboardButton("🏡 О жизни в СПб")
    button7 = types.KeyboardButton("📋 Учреждения")
    button8 = types.KeyboardButton("🔎 Поиск")
    

    keyboard.add(button1, button2, button3, button4, button5, button6, button7, button8)
    return keyboard


@bot.message_handler(commands=['start'])
def start_bot(message):
    welcome_text = """
🤖 <b> Привет! Я ваш помощник по Санкт-Петергу!</b>
   
Я могу помочь с:
• Государственными услугами
• Социальной поддержкой
• Транспортом города
• Мероприятиями
• Ответами на вопросы

<b>Выберите раздел ниже 👇</b>
    """

    bot.send_message(message.chat.id, welcome_text, parse_mode='HTML', reply_markup=create_menu())

@bot.message_handler(func=lambda message: message.text == "🏛️ Госуслуги")
def gosuslugi_info(message):
    bot.send_message(message.chat.id, "🏛️ Выберите раздел госуслуг:", reply_markup=createGosMenu())
    # Обновляем данные в фоне (если нужно по 30-дневному расписанию)
    def _update_data():
        try:
            os_manager.ensure_data_loaded()
        except Exception as e:
            print(f"[bot] Ошибка при обновлении данных: {e}")
    import threading
    threading.Thread(target=_update_data, daemon=True).start()

@bot.message_handler(func=lambda message: message.text == "💰 Соцподдержка")
def social_support(message):
    bot.send_message(message.chat.id, "💰 Выберите категорию соцподдержки:", reply_markup=createSocialMenu())
    # Обновляем данные в фоне
    def _update_data():
        try:
            os_manager.ensure_data_loaded()
        except Exception as e:
            print(f"[bot] Ошибка при обновлении данных: {e}")
    import threading
    threading.Thread(target=_update_data, daemon=True).start()

@bot.message_handler(func=lambda message: message.text == "🚇 Транспорт")
def transport_info(message):
    bot.send_message(message.chat.id, "🚇 Выберите вид транспорта:", reply_markup=createTransportMenu())
    # Обновляем данные в фоне
    def _update_data():
        try:
            os_manager.ensure_data_loaded()
        except Exception as e:
            print(f"[bot] Ошибка при обновлении данных: {e}")
    import threading
    threading.Thread(target=_update_data, daemon=True).start()

@bot.message_handler(func=lambda message: message.text == "🎭 Мероприятия")
def events_info(message):
    bot.send_message(message.chat.id, "🎭 Выберите тип мероприятия:", reply_markup=createIventsMenu())
    # Обновляем данные в фоне
    def _update_data():
        try:
            os_manager.ensure_data_loaded()
        except Exception as e:
            print(f"[bot] Ошибка при обновлении данных: {e}")
    import threading
    threading.Thread(target=_update_data, daemon=True).start()

@bot.message_handler(func=lambda message: message.text == "❓ FAQ")
def faq_info(message):
    text = """
<b> ❓ Часто задаваемые вопросы</b>

🤔 <b>Как получить справку?</b>
📍 Обратитесь в МФЦ с паспортом

🏠 <b>Куда жаловаться на ЖКХ?</b>
📍 Горячая линия: 8-800-100-00-00

🏥 <b>Как записаться к врачу?</b>
📍 Через портал Госуслуги

📝 <b>Нужна ли регистрация?</b>
📍 Да, для получения услуг требуется регистрация в СПб

🚗 <b>Где оформить парковочное разрешение?</b>
📍 Через портал "Госуслуги" или МФЦ
    """
    bot.send_message(message.chat.id, text, parse_mode = 'HTML')

@bot.message_handler(func=lambda message: message.text == "🏡 О жизни в СПб")
def city_life(message):
    text = """
    <b>🏡 Жизнь в Санкт-Петербурге</b>

📋 <b>Правила:</b>
• Регистрация в течение 7 дней после переезда
• Тишина с 23:00 до 8:00
• Раздельный сбор мусора (в тестовом режиме)

🏛️ <b>Сервисы:</b>
• МФЦ - многофункциональные центры
• Госуслуги - электронные услуги
• Соцзащита - поддержка населения

    
🚨 <b>Экстренные службы:</b>
• 112 - Единая служба спасения
• 103 - Скорая помощь
• 102 - Полиция
    """
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda message: message.text == "📋 Учреждения")
def establishments_info(message):
    bot.send_message(message.chat.id, "📋 Выберите тип учреждения:", reply_markup=createEstablishmentsMenu())

@bot.message_handler(content_types=['text'])
def handle_text_commands(message):
    # Normalize spaces and lowercase for reliable matching
    raw_text = message.text or ""
    normalized = ' '.join(raw_text.split()).lower()
    user_text = normalized

    if user_text in ['госуслуги','gosuslugi','услуги']:
        gosuslugi_info(message)
    elif user_text in ['соцподдержка','social','поддержка']:
        social_support(message)
    elif user_text in ['транспорт', 'transport', 'метро','автобус']:
        transport_info(message)
    elif user_text in ['мероприятия', 'events', 'афиша', 'события']:
        events_info(message)
    elif user_text in ['faq', 'частые вопросы', 'вопросы']:
        faq_info(message)
    elif user_text in ['о жизни в спб', 'жизнь в спб', 'спб', 'санкт-петербург', 'петербург']:
        city_life(message)
    elif user_text in ['учреждения', 'заведения', 'учреждение', 'организации']:
        establishments_info(message)
    elif user_text in ['старт', 'start', 'начать', 'главное меню'] or 'назад' in user_text:
        # Treat any 'назад' (back) as a request to return to main menu
        start_bot(message)
    else:
        # If command is not recognized - treat as open query and forward to parser+AI pipeline
        process_open_query(message)
        return
        
        # If we somehow return here, show simple help
        help_text = """
🤔 <b>Я не совсем понял ваш запрос.</b>

Вы можете:
• Написать одну из команд: <i>Госуслуги, Транспорт, Мероприятия, FAQ</i>
• Использовать кнопки меню ниже
• Написать <i>«Старт»</i> для возврата в главное меню
        """
        bot.send_message(message.chat.id, help_text, parse_mode='HTML', reply_markup=create_menu())


def process_open_query(message):
    """Process free-form queries with OpenSearch -> LLM -> Telegram reply."""
    user_input = message.text.strip()
    chat_id = message.chat.id

    # Maintain chat history per user
    if 'user_histories' not in globals():
        global user_histories
        user_histories = {}
    if chat_id not in user_histories:
        user_histories[chat_id] = []

    # Шаг 1: Проверяем локальные данные в OpenSearch (30 дней кеш)
    try:
        os_manager.ensure_data_loaded()
    except Exception as e:
        print(f"[bot] Ошибка при инициализации OpenSearch: {e}")

    # Шаг 2: Ищем в OpenSearch локально
    try:
        bot.send_chat_action(chat_id, 'typing')
        search_results = os_manager.search(user_input, size=7)
        
        if search_results:
            # Формируем контекст из результатов поиска
            context_parts = []
            for i, hit in enumerate(search_results, 1):
                s = hit['_source']
                title = s.get('title', 'Без названия')
                content = s.get('content', '')[:200]
                address = s.get('address', '')
                category = s.get('category', '')
                
                details = f"{i}. {title}"
                if category:
                    details += f" ({category})"
                if address:
                    details += f"\n   📍 {address}"
                if content:
                    details += f"\n   📝 {content}..."
                context_parts.append(details)
            
            extra_context = "\n\n".join(context_parts)
        else:
            extra_context = ""
    except Exception as e:
        print(f"[bot] Ошибка при поиске в OpenSearch: {e}")
        extra_context = ""

    # Шаг 3: Если нет результатов в кеше - запускаем парсинг в фоне
    if not search_results:
        bot.send_message(chat_id, "Данные обновляются, попробуйте повторить запрос через минуту...")
        
        def _background_update():
            try:
                os_manager.load_all_data()
                os_manager.update_metadata()
                print("[bot] Данные обновлены")
            except Exception as e:
                print(f"[bot] Ошибка при обновлении: {e}")
        
        import threading
        threading.Thread(target=_background_update, daemon=True).start()
        return

    # Шаг 4: Отправляем в LLM с контекстом из локальной базы
    try:
        answer = ask_agent(user_input, chat_history=user_histories.get(chat_id, []), extra_context=extra_context)
        
        # Сохраняем в историю
        user_histories.setdefault(chat_id, []).append(HumanMessage(content=user_input))
        user_histories[chat_id].append(AIMessage(content=answer))
        if len(user_histories[chat_id]) > 6:
            user_histories[chat_id] = user_histories[chat_id][-6:]
        
        # Отправляем ответ
        if isinstance(answer, str):
            to_send = answer[:4000]
        else:
            to_send = str(answer)[:4000]
        bot.send_message(chat_id, to_send)
    except Exception as e:
        bot.send_message(chat_id, f"Ошибка при обработке запроса: {e}")
        print(f"[bot] Ошибка в ask_agent: {e}")

print("Бот запущен! Нажмите Ctrl+C чтобы остановить")
bot.polling(none_stop = True)
