import logging
import sys
import time
from spb_bot_opensearch.opensearch_manager import OpenSearchManager

# Настройка красивого вывода логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    print("🚀 --- ЗАПУСК ОБНОВЛЕНИЯ БАЗЫ ДАННЫХ ---")
    
    # 1. Инициализация менеджера
    try:
        os_manager = OpenSearchManager()
    except Exception as e:
        logger.error(f"Не удалось подключиться к OpenSearch: {e}")
        return

    # 2. Удаление старого индекса (Полная очистка)
    # Это важно, чтобы данные не дублировались при повторных запусках
    if os_manager.client.indices.exists(index=os_manager.index_name):
        print(f"🗑️  Удаляю старый индекс '{os_manager.index_name}'...")
        os_manager.client.indices.delete(index=os_manager.index_name)
    else:
        print(f"✨ Индекса '{os_manager.index_name}' еще нет, создаем новый.")

    # 3. Создание индекса заново (с правильными полями address, phone и т.д.)
    print("⚙️  Настройка схемы индекса...")
    os_manager.setup_index()
    
    # 4. Загрузка данных
    print("📂 Читаю файлы из папки data и загружаю в OpenSearch...")
    start_time = time.time()
    
    os_manager.load_all_data()
    
    end_time = time.time()
    print(f"⏱️  Загрузка заняла {end_time - start_time:.2f} сек.")
    
    # 5. Статистика
    print("\n📊 ИТОГОВАЯ СТАТИСТИКА:")
    stats = os_manager.get_statistics()
    print(f"Всего документов: {stats.get('total_documents', 0)}")
    
    print("По категориям:")
    for cat, count in stats.get('categories', {}).items():
        print(f"  - {cat.upper()}: {count}")
    
    # 6. Тестовый поиск (проверка)
    test_query = "паспорт"
    print(f"\n🔎 Тестовый поиск по слову '{test_query}':")
    results = os_manager.search(test_query, size=1)
    
    if results:
        hit = results[0]['_source']
        print(f"   Найдено: {hit.get('title')}")
        print(f"   Категория: {hit.get('category')}")
    else:
        print("   Ничего не найдено (возможно, в базе нет слова 'паспорт')")

    print("\n✅ Система готова к работе!")

if __name__ == "__main__":
    main()