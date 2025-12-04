"""
VK бот для Санкт-Петербурга
"""
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import json
import threading
import sys
import os

# Добавляем путь к корневой директории проекта
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Импортируем общие модули
from ai_engine import ask_agent
from spb_bot_opensearch.opensearch_manager import OpenSearchManager
from langchain_core.messages import HumanMessage, AIMessage

# Токен ВКонтакте
VK_TOKEN = "vk1.a.AYjSJn_GMEKM5y8P15dAp14bgZbvKrUujNpS1wC8ShXG8XE0cOZ6gfLjywiN1qeh3A1I8uX2Q41BBcFu0neea_Zj4dqv9zCj06YiNInD-bA2mJl5eUya6fQpstw5zfxOHha9rxkI-AGK8sm4f11-Q40h8QS2ZAnvh23YB6taP9yYZLU7fFWwJ4GSYc7rGVS4efoSAN7d6PwY96Vsek0ejQ"
GROUP_ID = 0  # Можно указать ID группы, если нужно

class VKBot:
    def __init__(self, token):
        self.vk_session = vk_api.VkApi(token=token)
        self.longpoll = VkLongPoll(self.vk_session)
        self.vk = self.vk_session.get_api()
        self.os_manager = OpenSearchManager()
        self.user_histories = {}
        self.keyboards = {}
        
        # Создаем клавиатуры
        self._create_keyboards()
        
    def _create_keyboards(self):
        """Создание клавиатур для VK"""
        # Главное меню
        main_keyboard = VkKeyboard(one_time=False)
        main_keyboard.add_button('🏛️ Госуслуги', color=VkKeyboardColor.PRIMARY)
        main_keyboard.add_button('💰 Соцподдержка', color=VkKeyboardColor.PRIMARY)
        main_keyboard.add_line()
        main_keyboard.add_button('🚇 Транспорт', color=VkKeyboardColor.PRIMARY)
        main_keyboard.add_button('🎭 Мероприятия', color=VkKeyboardColor.PRIMARY)
        main_keyboard.add_line()
        main_keyboard.add_button('❓ FAQ', color=VkKeyboardColor.SECONDARY)
        main_keyboard.add_button('🏡 О жизни в СПб', color=VkKeyboardColor.SECONDARY)
        main_keyboard.add_line()
        main_keyboard.add_button('📋 Учреждения', color=VkKeyboardColor.PRIMARY)
        main_keyboard.add_button('🔎 Поиск', color=VkKeyboardColor.POSITIVE)
        self.keyboards['main'] = main_keyboard.get_keyboard()
        
        # Меню транспорта
        transport_keyboard = VkKeyboard(one_time=False)
        transport_keyboard.add_button('Карта Метро', color=VkKeyboardColor.PRIMARY)
        transport_keyboard.add_button('Автобусы', color=VkKeyboardColor.PRIMARY)
        transport_keyboard.add_line()
        transport_keyboard.add_button('Трамваи', color=VkKeyboardColor.PRIMARY)
        transport_keyboard.add_button('Парковки', color=VkKeyboardColor.PRIMARY)
        transport_keyboard.add_line()
        transport_keyboard.add_button('Назад в главное меню', color=VkKeyboardColor.NEGATIVE)
        self.keyboards['transport'] = transport_keyboard.get_keyboard()
        
        # Меню госуслуг
        gos_keyboard = VkKeyboard(one_time=False)
        gos_keyboard.add_button('Регистрация', color=VkKeyboardColor.PRIMARY)
        gos_keyboard.add_button('Документы', color=VkKeyboardColor.PRIMARY)
        gos_keyboard.add_line()
        gos_keyboard.add_button('Медицина', color=VkKeyboardColor.PRIMARY)
        gos_keyboard.add_button('Семья', color=VkKeyboardColor.PRIMARY)
        gos_keyboard.add_line()
        gos_keyboard.add_button('Жилье', color=VkKeyboardColor.PRIMARY)
        gos_keyboard.add_button('Назад в главное меню', color=VkKeyboardColor.NEGATIVE)
        self.keyboards['gos'] = gos_keyboard.get_keyboard()
        
        # Меню соцподдержки
        social_keyboard = VkKeyboard(one_time=False)
        social_keyboard.add_button('Пенсионерам', color=VkKeyboardColor.PRIMARY)
        social_keyboard.add_button('Детям', color=VkKeyboardColor.PRIMARY)
        social_keyboard.add_line()
        social_keyboard.add_button('Студентам', color=VkKeyboardColor.PRIMARY)
        social_keyboard.add_button('Субсидии ЖКХ', color=VkKeyboardColor.PRIMARY)
        social_keyboard.add_line()
        social_keyboard.add_button('Пособия', color=VkKeyboardColor.PRIMARY)
        social_keyboard.add_button('Назад в главное меню', color=VkKeyboardColor.NEGATIVE)
        self.keyboards['social'] = social_keyboard.get_keyboard()
        
        # Меню мероприятий
        events_keyboard = VkKeyboard(one_time=False)
        events_keyboard.add_button('Театры', color=VkKeyboardColor.PRIMARY)
        events_keyboard.add_button('Выставки', color=VkKeyboardColor.PRIMARY)
        events_keyboard.add_line()
        events_keyboard.add_button('Кинотеатры', color=VkKeyboardColor.PRIMARY)
        events_keyboard.add_button('Фестивали', color=VkKeyboardColor.PRIMARY)
        events_keyboard.add_line()
        events_keyboard.add_button('Назад в главное меню', color=VkKeyboardColor.NEGATIVE)
        self.keyboards['events'] = events_keyboard.get_keyboard()
        
        # Меню учреждений
        establishments_keyboard = VkKeyboard(one_time=False)
        establishments_keyboard.add_button('Детские сады', color=VkKeyboardColor.PRIMARY)
        establishments_keyboard.add_button('Школы', color=VkKeyboardColor.PRIMARY)
        establishments_keyboard.add_line()
        establishments_keyboard.add_button('Колледжи', color=VkKeyboardColor.PRIMARY)
        establishments_keyboard.add_button('Вузы', color=VkKeyboardColor.PRIMARY)
        establishments_keyboard.add_line()
        establishments_keyboard.add_button('Назад в главное меню', color=VkKeyboardColor.NEGATIVE)
        self.keyboards['establishments'] = establishments_keyboard.get_keyboard()

    def send_message(self, user_id, message, keyboard=None, attachment=None):
        """Отправка сообщения пользователю"""
        try:
            params = {
                'user_id': user_id,
                'message': message,
                'random_id': 0
            }
            if keyboard:
                params['keyboard'] = json.dumps(keyboard)
            if attachment:
                params['attachment'] = attachment
            
            self.vk.messages.send(**params)
        except Exception as e:
            print(f"[VK Bot] Ошибка отправки сообщения: {e}")

    def handle_start(self, user_id):
        """Обработка команды /start"""
        welcome_text = """🤖 Привет! Я ваш помощник по Санкт-Петербургу!

Я могу помочь с:
• Государственными услугами
• Социальной поддержкой
• Транспортом города
• Мероприятиями
• Ответами на вопросы

Выберите раздел ниже 👇"""
        self.send_message(user_id, welcome_text, self.keyboards['main'])

    def handle_gosuslugi(self, user_id):
        """Обработка госуслуг"""
        self.send_message(user_id, "🏛️ Выберите раздел госуслуг:", self.keyboards['gos'])
        self._update_data_background()

    def handle_social(self, user_id):
        """Обработка соцподдержки"""
        self.send_message(user_id, "💰 Выберите категорию соцподдержки:", self.keyboards['social'])
        self._update_data_background()

    def handle_transport(self, user_id):
        """Обработка транспорта"""
        self.send_message(user_id, "🚇 Выберите вид транспорта:", self.keyboards['transport'])
        self._update_data_background()

    def handle_events(self, user_id):
        """Обработка мероприятий"""
        self.send_message(user_id, "🎭 Выберите тип мероприятия:", self.keyboards['events'])
        self._update_data_background()

    def handle_faq(self, user_id):
        """Обработка FAQ"""
        faq_text = """❓ Часто задаваемые вопросы

🤔 Как получить справку?
📍 Обратитесь в МФЦ с паспортом

🏠 Куда жаловаться на ЖКХ?
📍 Горячая линия: 8-800-100-00-00

🏥 Как записаться к врачу?
📍 Через портал Госуслуги

📝 Нужна ли регистрация?
📍 Да, для получения услуг требуется регистрация в СПб

🚗 Где оформить парковочное разрешение?
📍 Через портал "Госуслуги" или МФЦ"""
        self.send_message(user_id, faq_text)

    def handle_city_life(self, user_id):
        """Обработка информации о жизни в СПб"""
        city_text = """🏡 Жизнь в Санкт-Петербурге

📋 Правила:
• Регистрация в течение 7 дней после переезда
• Тишина с 23:00 до 8:00
• Раздельный сбор мусора (в тестовом режиме)

🏛️ Сервисы:
• МФЦ - многофункциональные центры
• Госуслуги - электронные услуги
• Соцзащита - поддержка населения

🚨 Экстренные службы:
• 112 - Единая служба спасения
• 103 - Скорая помощь
• 102 - Полиция"""
        self.send_message(user_id, city_text)

    def handle_establishments(self, user_id):
        """Обработка учреждений"""
        self.send_message(user_id, "📋 Выберите тип учреждения:", self.keyboards['establishments'])

    def _update_data_background(self):
        """Обновление данных в фоне"""
        def _update():
            try:
                self.os_manager.ensure_data_loaded()
            except Exception as e:
                print(f"[VK Bot] Ошибка при обновлении данных: {e}")
        
        threading.Thread(target=_update, daemon=True).start()

    def process_open_query(self, user_id, user_input):
        """Обработка свободных запросов (поиск + ИИ)"""
        # Поддерживаем историю диалога
        if user_id not in self.user_histories:
            self.user_histories[user_id] = []

        # Шаг 1: Проверяем данные в OpenSearch
        try:
            self.os_manager.ensure_data_loaded()
        except Exception as e:
            print(f"[VK Bot] Ошибка OpenSearch: {e}")

        # Шаг 2: Ищем в OpenSearch
        try:
            search_results = self.os_manager.search(user_input, size=7)
            
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
                        details += f"\n📍 {address}"
                    if content:
                        details += f"\n📝 {content}..."
                    context_parts.append(details)
                
                extra_context = "\n\n".join(context_parts)
            else:
                extra_context = ""
        except Exception as e:
            print(f"[VK Bot] Ошибка при поиске: {e}")
            extra_context = ""

        # Шаг 3: Если нет результатов - запускаем обновление
        if not search_results:
            self.send_message(user_id, "Данные обновляются, попробуйте повторить запрос через минуту...")
            
            def _background_update():
                try:
                    self.os_manager.load_all_data()
                    self.os_manager.update_metadata()
                    print("[VK Bot] Данные обновлены")
                except Exception as e:
                    print(f"[VK Bot] Ошибка при обновлении: {e}")
            
            threading.Thread(target=_background_update, daemon=True).start()
            return

        # Шаг 4: Отправляем в LLM
        try:
            answer = ask_agent(user_input, 
                             chat_history=self.user_histories.get(user_id, []), 
                             extra_context=extra_context)
            
            # Сохраняем в историю
            self.user_histories.setdefault(user_id, []).append(HumanMessage(content=user_input))
            self.user_histories[user_id].append(AIMessage(content=answer))
            if len(self.user_histories[user_id]) > 6:
                self.user_histories[user_id] = self.user_histories[user_id][-6:]
            
            # Отправляем ответ
            if isinstance(answer, str):
                to_send = answer[:4000]
            else:
                to_send = str(answer)[:4000]
            self.send_message(user_id, to_send, self.keyboards['main'])
        except Exception as e:
            self.send_message(user_id, f"Ошибка при обработке запроса: {str(e)[:200]}", self.keyboards['main'])
            print(f"[VK Bot] Ошибка в ask_agent: {e}")

    def handle_text_message(self, user_id, text):
        """Обработка текстовых сообщений"""
        text_lower = text.lower().strip()

        # Обработка команд
        if text_lower in ['start', 'старт', 'начать', 'главное меню', 'меню']:
            self.handle_start(user_id)
        elif text == '🏛️ Госуслуги' or text_lower in ['госуслуги', 'gosuslugi', 'услуги']:
            self.handle_gosuslugi(user_id)
        elif text == '💰 Соцподдержка' or text_lower in ['соцподдержка', 'social', 'поддержка']:
            self.handle_social(user_id)
        elif text == '🚇 Транспорт' or text_lower in ['транспорт', 'transport', 'метро', 'автобус']:
            self.handle_transport(user_id)
        elif text == '🎭 Мероприятия' or text_lower in ['мероприятия', 'events', 'афиша', 'события']:
            self.handle_events(user_id)
        elif text == '❓ FAQ' or text_lower in ['faq', 'частые вопросы', 'вопросы']:
            self.handle_faq(user_id)
        elif text == '🏡 О жизни в СПб' or text_lower in ['о жизни в спб', 'жизнь в спб', 'спб', 'санкт-петербург', 'петербург']:
            self.handle_city_life(user_id)
        elif text == '📋 Учреждения' or text_lower in ['учреждения', 'заведения', 'учреждение', 'организации']:
            self.handle_establishments(user_id)
        elif text == 'Назад в главное меню':
            self.handle_start(user_id)
        elif text == '🔎 Поиск':
            self.send_message(user_id, "🔍 Введите ваш поисковый запрос:", None)
        else:
            # Обработка подменю или свободного запроса
            if text in ['Карта Метро', 'Автобусы', 'Трамваи', 'Парковки',
                       'Регистрация', 'Документы', 'Медицина', 'Семья', 'Жилье',
                       'Пенсионерам', 'Детям', 'Студентам', 'Субсидии ЖКХ', 'Пособия',
                       'Театры', 'Выставки', 'Кинотеатры', 'Фестивали',
                       'Детские сады', 'Школы', 'Колледжи', 'Вузы']:
                # Для пунктов подменю используем поиск
                self.process_open_query(user_id, text)
            else:
                # Свободный запрос
                self.process_open_query(user_id, text)

    def run(self):
        """Запуск бота ВКонтакте"""
        print("[VK Bot] Бот ВКонтакте запущен!")
        
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                user_id = event.user_id
                text = event.text
                
                print(f"[VK Bot] Сообщение от {user_id}: {text}")
                
                # Обработка сообщения
                self.handle_text_message(user_id, text)

def main():
    """Основная функция запуска VK бота"""
    bot = VKBot(VK_TOKEN)
    bot.run()

if __name__ == "__main__":
    main()