#!/usr/bin/env python3
"""
Финальная проверка всех изменений
"""

FILES_CHECKED = {
    "spb_bot/bot.py": {
        "должен содержать": [
            "from spb_bot_opensearch.opensearch_manager import OpenSearchManager",
            "os_manager = OpenSearchManager()",
            "def process_open_query(message):",
            "os_manager.ensure_data_loaded()",
            "os_manager.search(user_input",
        ],
        "НЕ должен содержать": [
            "check_toxicity",
            "_spawn_agent_for_user",
            "parse_site_impl",
            "search_city_services",
        ]
    },
    
    "spb_bot_opensearch/opensearch_manager.py": {
        "должен содержать": [
            "from datetime import datetime, timedelta",
            "def is_index_empty(self)",
            "def is_index_expired(self)",
            "def update_metadata(self)",
            "def ensure_data_loaded(self)",
        ]
    },
    
    "ai_engine.py": {
        "должен содержать": [
            "os_manager.ensure_data_loaded()",
            "[ai_engine] ✅ Данные загружены",
        ]
    },
    
    "spb_bot_opensearch/initialize.py": {
        "должен существовать": True,
        "должен содержать": [
            "os_manager = OpenSearchManager()",
            "os_manager.setup_index()",
            "os_manager.load_all_data()",
            "os_manager.update_metadata()",
        ]
    }
}

DOCUMENTS = [
    "QUICKSTART.md",
    "ARCHITECTURE.md",
    "CHANGES.md",
    "IMPLEMENTATION_SUMMARY.md",
    "SUMMARY.md",
    "README_NEW_ARCHITECTURE.py",
    "check_config.py",
]

def check_file(filepath, requirements):
    """Проверяет файл на соответствие требованиям"""
    import os
    
    if not os.path.exists(filepath):
        return False, f"Файл не найден: {filepath}"
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем должен содержать
        for required_text in requirements.get("должен содержать", []):
            if required_text not in content:
                return False, f"Не найдено: {required_text}"
        
        # Проверяем НЕ должен содержать
        for forbidden_text in requirements.get("НЕ должен содержать", []):
            if forbidden_text in content:
                return False, f"Найдено (но не должно быть): {forbidden_text}"
        
        return True, "OK"
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 70)
    print("✅ ФИНАЛЬНАЯ ПРОВЕРКА ВСЕХ ИЗМЕНЕНИЙ")
    print("=" * 70)
    
    all_good = True
    
    # Проверка основных файлов
    print("\n📝 ПРОВЕРКА ИЗМЕНЁННЫХ ФАЙЛОВ:")
    print("-" * 70)
    for filepath, requirements in FILES_CHECKED.items():
        ok, msg = check_file(filepath, requirements)
        status = "✅" if ok else "❌"
        print(f"{status} {filepath:<50} {msg}")
        if not ok:
            all_good = False
    
    # Проверка документации
    print("\n📚 ПРОВЕРКА ДОКУМЕНТАЦИИ:")
    print("-" * 70)
    for doc in DOCUMENTS:
        import os
        exists = os.path.exists(doc)
        status = "✅" if exists else "❌"
        print(f"{status} {doc:<50} {'существует' if exists else 'НЕ найден'}")
        if not exists:
            all_good = False
    
    print("\n" + "=" * 70)
    if all_good:
        print("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
        print("\nСледующие шаги:")
        print("  1. python check_config.py")
        print("  2. python spb_bot_opensearch/initialize.py")
        print("  3. python spb_bot/bot.py")
    else:
        print("⚠️  ОБНАРУЖЕНЫ ПРОБЛЕМЫ - ПРОВЕРЬТЕ СПИСОК ВЫШЕ")
    print("=" * 70)

if __name__ == "__main__":
    import sys
    import os
    
    # Переходим в папку проекта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    main()
