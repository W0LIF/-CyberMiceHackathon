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
from ai_engine import check_toxicity, ask_agent, search_city_services, detect_category
from langchain_core.messages import HumanMessage, AIMessage
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


def _spawn_agent_for_user(chat_id, user_prompt, extra_context=None):
    """Run the agent in a background thread and send the answer to the chat when ready."""
    def _work():
        try:
            bot.send_chat_action(chat_id, 'typing')
            answer = ask_agent(user_prompt, chat_history=user_histories.get(chat_id, []), extra_context=extra_context or '')
            if isinstance(answer, str):
                bot.send_message(chat_id, answer[:4000])
            else:
                bot.send_message(chat_id, str(answer)[:4000])
            # Save to history
            user_histories.setdefault(chat_id, []).append(HumanMessage(content=user_prompt))
            user_histories[chat_id].append(AIMessage(content=answer))
            if len(user_histories[chat_id]) > 6:
                user_histories[chat_id] = user_histories[chat_id][-6:]
        except Exception as e:
            bot.send_message(chat_id, f"Произошла ошибка при обращении к агенту: {e}")
    import threading
    threading.Thread(target=_work, daemon=True).start()

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
    # Spawn agent to prepare a quick summary and start parsing for refresh
    summary_prompt = "Пожалуйста, дай краткий обзор государственных услуг Санкт-Петербурга и подскажи, где получить популярные услуги (паспорт, регистрация, МФЦ)."
    _spawn_agent_for_user(message.chat.id, summary_prompt, extra_context="REFRESH_PARSE: gu_spb_knowledge")
    # Trigger a one-shot parsing in background to refresh local cache
    try:
        import threading
        threading.Thread(target=lambda: ai_engine.parse_site_impl('gu_spb_knowledge'), daemon=True).start()
    except Exception:
        pass

@bot.message_handler(func=lambda message: message.text == "💰 Соцподдержка")
def social_support(message):
    bot.send_message(message.chat.id, "💰 Выберите категорию соцподдержки:", reply_markup=createSocialMenu())
    summary_prompt = "Пожалуйста, дай краткий обзор мер соцподдержки в Санкт-Петербурге: основные выплаты и куда обращаться."
    _spawn_agent_for_user(message.chat.id, summary_prompt, extra_context="REFRESH_PARSE: gov_spb_helper")
    try:
        import threading
        threading.Thread(target=lambda: ai_engine.parse_site_impl('gov_spb_helper'), daemon=True).start()
    except Exception:
        pass

@bot.message_handler(func=lambda message: message.text == "🚇 Транспорт")
def transport_info(message):
    bot.send_message(message.chat.id, "🚇 Выберите вид транспорта:", reply_markup=createTransportMenu())
    summary_prompt = "Пожалуйста, дай краткий обзор транспорта Петербурга: метро, автобусы, расписания, где искать информацию о пробках и ремонтах дорог."
    _spawn_agent_for_user(message.chat.id, summary_prompt)

@bot.message_handler(func=lambda message: message.text == "🎭 Мероприятия")
def events_info(message):
    bot.send_message(message.chat.id, "🎭 Выберите тип мероприятия:", reply_markup=createIventsMenu())
    summary_prompt = "Подскажи ближайшие интересные мероприятия в Петербурге и где посмотреть афишу."
    _spawn_agent_for_user(message.chat.id, summary_prompt)

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
    user_text = message.text.lower().strip()

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
    elif user_text in ['старт', 'start', 'начать', 'главное меню']:
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
    """Process free-form queries with parsing -> LLM -> Telegram reply."""
    user_input = message.text.strip()

    # Toxicity check
    if check_toxicity(user_input):
        bot.send_message(message.chat.id, "Извините, я не могу ответить на это.")
        return

    # Maintain chat history per user
    if 'user_histories' not in globals():
        global user_histories
        user_histories = {}
    chat_id = message.chat.id
    if chat_id not in user_histories:
        user_histories[chat_id] = []

    # Quick search via city services (fast API) — detect likely categories to reduce noise
    categories = detect_category(user_input)
    api_context_parts = []
    # limit the number of categories to avoid excessive calls
    for cat in categories[:3]:
        try:
            api_result = search_city_services(user_input, cat)
            if api_result and 'ничего не найдено' not in api_result.lower():
                api_context_parts.append(f"[{cat}] {api_result}")
        except Exception as e:
            print(f"Ошибка при поиске по API {cat}: {e}")

    api_context = "\n\n".join(api_context_parts)

    # Search in parsed JSON files as additional context (if cached)
    parsed_context_parts = []
    parser = UniversalParser()
    parsed_files = [
        'parsing/gu_spb_knowledge.json',
        'parsing/gu_spb_mfc.json',
        'parsing/gov_spb_helper.json',
        'parsing/consultant.json'
    ]
    for pf in parsed_files:
        if os.path.exists(pf):
            try:
                with open(pf, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        title = (item.get('title') or item.get('name') or '')
                        content = (item.get('content') or item.get('text') or item.get('description') or '')
                        link = item.get('link') or item.get('href') or ''
                        combined = f"{title} {content} {link}".lower()
                        if user_input.lower() in combined:
                            snippet = content[:300].strip() if content else title
                            parsed_context_parts.append(f"- {title} ({link})\n{snippet}")
                            if len(parsed_context_parts) >= 5:
                                break
            except Exception as e:
                print(f"Ошибка чтения parsed file {pf}: {e}")

    # If no cached parsed data found, try to parse one of the key sites (non-blocking to be safe)
    if not parsed_context_parts:
        # If background parser is enabled, trigger an update and ask user to try later
        if os.getenv('START_PARSER_BACKGROUND', 'false').lower() in ('1', 'true', 'yes'):
            bot.send_message(chat_id, "Я обновляю кеш данных в фоновом режиме — попробуйте снова через минуты 1-2.")
            return

        # Otherwise, start a one-shot parsing in background (do not block the bot)
        try:
            bot.send_message(chat_id, "Я не нашел локальных данных — запускаю парсинг в фоне. Попробуйте повторить запрос через минуту.")
            def _one_shot_parse():
                try:
                    items = parser.parse_site(CONFIGURATIONS['gu_spb_knowledge'])
                    for item in items:
                        title = item.get('title','')
                        content = item.get('content') or ''
                        link = item.get('link') or ''
                        combined = f"{title} {content} {link}".lower()
                        if user_input.lower() in combined:
                            parsed_context_parts.append(f"- {title} ({link})\n{content[:300]}")
                            if len(parsed_context_parts) >= 5:
                                break
                except Exception as e:
                    print(f"Ошибка при одноразовом парсинге: {e}")
            import threading
            threading.Thread(target=_one_shot_parse, daemon=True).start()
            # Also trigger a background parse for the top detected category to speed up future queries
            try:
                top_cat = categories[0]
                cat_to_config = {
                    'documents': ['gu_spb_mfc', 'gu_spb_knowledge'],
                    'social': ['gov_spb_helper'],
                    'iparent': ['gu_spb_mfc', 'gu_spb_knowledge'],
                    'pets': ['consultant'],
                    'health': ['consultant']
                }
                configs = cat_to_config.get(top_cat, [])
                if configs:
                    import ai_engine as _ae
                    import threading as _th
                    for cfg in configs[:1]:
                        _th.Thread(target=lambda c=cfg: _ae.parse_site_impl(c), daemon=True).start()
            except Exception:
                pass
            return
        except Exception as e:
            print(f"Ошибка при запуске фоновго парсинга: {e}")

    parsed_context = "\n\n".join(parsed_context_parts)

    # Combine contexts for LLM
    extra_context_list = []
    if api_context:
        extra_context_list.append(api_context)
    if parsed_context:
        extra_context_list.append(parsed_context)

    extra_context = "\n\n".join(extra_context_list)

    # Build chat history (LangChain message objects) for the agent
    history_messages = user_histories.get(chat_id, [])
    # Call the agent (GigaChat) with extra_context
    bot.send_chat_action(chat_id, 'typing')
    answer = ask_agent(user_input, chat_history=history_messages, extra_context=extra_context)

    # Save to history
    user_histories.setdefault(chat_id, []).append(HumanMessage(content=user_input))
    user_histories[chat_id].append(AIMessage(content=answer))
    # Keep only last 6 messages
    if len(user_histories[chat_id]) > 6:
        user_histories[chat_id] = user_histories[chat_id][-6:]

    # Respond in chat (limit to 4096 characters for Telegram)
    if isinstance(answer, str):
        to_send = answer[:4000]
    else:
        to_send = str(answer)[:4000]
    bot.send_message(chat_id, to_send)

print("Бот запущен! Нажмите Ctrl+C чтобы остановить")
bot.polling(none_stop = True)
