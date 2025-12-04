#!/usr/bin/env python3
"""
Скрипт инициализации OpenSearch индекса
Загружает все данные из папки /data и сохраняет в OpenSearch
"""
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

logger = logging.getLogger(__name__)

def main():
    """Основная функция инициализации"""
    print("=" * 50)
    print("Инициализация OpenSearch системы")
    print("=" * 50)
    
    try:
        # Создаем менеджер
        os_manager = OpenSearchManager()
        
        # 1. Настраиваем индекс
        print("\n1. Настройка индекса...")
        os_manager.setup_index()
        print("   OK: Индекс готов")
        
        # 2. Загружаем данные
        print("\n2. Загрузка данных из JSON файлов...")
        os_manager.load_all_data()
        print("   OK: Данные загружены")
        
        # 3. Обновляем метаданные
        print("\n3. Сохранение метаданных...")
        os_manager.update_metadata()
        print("   OK: Метаданные сохранены")
        
        print("\n" + "=" * 50)
        print("OK: Система OpenSearch готова к работе!")
        print("=" * 50)
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"\nОшибка при инициализации: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
