import telebot
from telebot import types
import requests
import json
from submenu import*
TOKEN = "8482065670:AAHcPeR6v20gFlgQCtfYz3uxfZY3QG4CSGo"
bot = telebot.TeleBot(TOKEN)

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

@bot.message_handler(func=lambda message: message.text == "💰 Соцподдержка")
def social_support(message):
   bot.send_message(message.chat.id, "💰 Выберите категорию соцподдержки:", reply_markup=createSocialMenu())

@bot.message_handler(func=lambda message: message.text == "🚇 Транспорт")
def transport_info(message):
    bot.send_message(message.chat.id, "🚇 Выберите вид транспорта:", reply_markup=createTransportMenu())

@bot.message_handler(func=lambda message: message.text == "🎭 Мероприятия")
def events_info(message):
    bot.send_message(message.chat.id, "🎭 Выберите тип мероприятия:", reply_markup=createIventsMenu())

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
        # Если команда не распознана, показываем главное меню с подсказкой
        help_text = """
🤔 <b>Я не совсем понял ваш запрос.</b>

Вы можете:
• Написать одну из команд: <i>Госуслуги, Транспорт, Мероприятия, FAQ</i>
• Использовать кнопки меню ниже
• Написать <i>«Старт»</i> для возврата в главное меню
        """
        bot.send_message(message.chat.id, help_text, parse_mode='HTML', reply_markup=create_menu())

print("Бот запущен! Нажмите Ctrl+C чтобы остановить")
bot.polling(none_stop = True)
