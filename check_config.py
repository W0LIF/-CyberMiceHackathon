#!/usr/bin/env python3
"""
Проверка конфигурации системы перед запуском
"""
import os
import sys
from pathlib import Path

def check_opensearch_connection():
    """Проверяет подключение к OpenSearch"""
    try:
        from opensearchpy import OpenSearch
        import warnings
        warnings.filterwarnings('ignore')
        client = OpenSearch(
            hosts=[{'host': 'localhost', 'port': 9200}],
            http_auth=('admin', 'admin'),
            use_ssl=True,
            verify_certs=False
        )
        if client.ping():
            print("OK: OpenSearch: подключение успешно")
            return True
    except Exception as e:
        print(f"ОШИБКА: OpenSearch: {e}")
        return False

def check_data_folder():
    """Проверяет наличие папки data"""
    data_path = Path(__file__).parent / "data"
    if data_path.exists():
        json_count = len(list(data_path.glob("*.json")))
        print(f"OK: Папка data найдена ({json_count} JSON файлов)")
        return True
    else:
        print(f"ОШИБКА: Папка data не найдена: {data_path}")
        return False

def check_required_packages():
    """Проверяет установку необходимых пакетов"""
    packages = [
        'telebot',
        'opensearchpy',
        'langchain',
        'langchain_gigachat',
        'requests'
    ]
    all_ok = True
    for pkg in packages:
        try:
            __import__(pkg)
            print(f"OK: {pkg}: установлен")
        except ImportError:
            print(f"ОШИБКА: {pkg}: НЕ установлен")
            all_ok = False
    return all_ok

def check_configuration_files():
    """Проверяет наличие конфиг файлов"""
    root = Path(__file__).parent
    files_to_check = [
        root / "spb_bot" / "bot.py",
        root / "spb_bot_opensearch" / "opensearch_manager.py",
        root / "spb_bot_opensearch" / "initialize.py",
        root / "ai_engine.py"
    ]
    all_ok = True
    for file in files_to_check:
        if file.exists():
            print(f"OK: {file.name}: найден")
        else:
            print(f"ОШИБКА: {file.name}: НЕ найден ({file})")
            all_ok = False
    return all_ok

def main():
    print("=" * 50)
    print("Проверка конфигурации системы")
    print("=" * 50)
    
    print("\nПакеты:")
    pkg_ok = check_required_packages()
    
    print("\nФайлы:")
    cfg_ok = check_configuration_files()
    
    print("\nДанные:")
    data_ok = check_data_folder()
    
    print("\nПодключение:")
    db_ok = check_opensearch_connection()
    
    print("\n" + "=" * 50)
    if pkg_ok and cfg_ok and data_ok and db_ok:
        print("OK: ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ - МОЖНО ЗАПУСКАТЬ БОТ")
    else:
        print("ОШИБКА: НУЖНО ИСПРАВИТЬ")
        if not db_ok:
            print("   -> Убедитесь, что OpenSearch запущен на localhost:9200")
        if not data_ok:
            print("   -> Проверьте наличие папки data в корне проекта")
        if not pkg_ok:
            print("   -> Установите необходимые пакеты: pip install -r requirements.txt")
    print("=" * 50)

if __name__ == "__main__":
    # Добавляем корень проекта в путь
    root = Path(__file__).parent.parent
    sys.path.insert(0, str(root))
    main()
