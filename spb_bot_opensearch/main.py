# main.py
import logging
import sys
from opensearch_manager import OpenSearchManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('opensearch.log')
    ]
)

def main():
    """Основная функция инициализации"""
    print(" Инициализация OpenSearch системы...")
    
    # Создаем менеджер
    os_manager = OpenSearchManager()
    
    # 1. Настраиваем индекс
    print("1. Настройка индекса...")
    os_manager.setup_index()
    
    # 2. Загружаем данные
    print("2. Загрузка данных из JSON файлов...")
    os_manager.load_all_data()
    
    # 3. Очищаем старые данные
    print("3. Очистка устаревших данных...")
    os_manager.cleanup_old_data()
    
    # 4. Показываем статистику
    print("4. Получение статистики...")
    stats = os_manager.get_statistics()
    
    print("\n СТАТИСТИКА:")
    print(f"Всего документов: {stats.get('total_documents', 0)}")
    print("По категориям:")
    for cat, count in stats.get('categories', {}).items():
        print(f"  - {cat}: {count} документов")
    
    # 5. Тестовый поиск
    print("\n Тестовый поиск:")
    results = os_manager.search("паспорт", size=2)
    
    if results:
        for i, hit in enumerate(results, 1):
            source = hit['_source']
            print(f"\n{i}. {source.get('title', 'Без названия')}")
            print(f"   Категория: {source.get('category', 'Не указана')}")
            print(f"   Ссылка: {source.get('link', 'Нет ссылки')}")
    else:
        print("   Поиск не дал результатов")
    
    print("\n Система OpenSearch готова к работе!")

if __name__ == "__main__":
    main()