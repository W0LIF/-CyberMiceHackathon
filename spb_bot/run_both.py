"""
Запуск обоих ботов (Telegram и VK) одновременно
"""
import threading
import sys
import os

# Добавляем путь к корневой директории проекта
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

def run_telegram_bot():
    """Запуск Telegram бота"""
    try:
        from bot import bot
        print("[Main] Запуск Telegram бота...")
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"[Main] Ошибка в Telegram боте: {e}")

def run_vk_bot():
    """Запуск VK бота"""
    try:
        from vk_bot import VKBot
        print("[Main] Запуск VK бота...")
        
        VK_TOKEN = "db40L1WRa3I0mmOdUcnF"
        bot = VKBot(VK_TOKEN)
        bot.run()
    except Exception as e:
        print(f"[Main] Ошибка в VK боте: {e}")

def main():
    """Основная функция для запуска обоих ботов"""
    print("=" * 50)
    print("Запуск мультиплатформенного бота для Санкт-Петербурга")
    print("=" * 50)
    
    # Создаем потоки для каждого бота
    tg_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    vk_thread = threading.Thread(target=run_vk_bot, daemon=True)
    
    # Запускаем потоки
    tg_thread.start()
    vk_thread.start()
    
    # Ожидаем завершения (или Ctrl+C)
    try:
        tg_thread.join()
        vk_thread.join()
    except KeyboardInterrupt:
        print("\n[Main] Боты остановлены пользователем")
    except Exception as e:
        print(f"[Main] Ошибка: {e}")

if __name__ == "__main__":
    main()