from opensearchpy import OpenSearch
import urllib3

# Отключаем надоедливые предупреждения о небезпечном SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# НАСТРОЙКИ (Должны совпадать с opensearch_manager.py)
HOST = 'localhost'
PORT = 9200
AUTH = ('admin', 'admin') # Попробуйте 'admin', если не сработает - 'admin123'

client = OpenSearch(
    hosts=[{'host': HOST, 'port': PORT}],
    http_auth=AUTH,
    use_ssl=True,           # <--- ВАЖНО: Включаем HTTPS
    verify_certs=False,     # <--- ВАЖНО: Отключаем проверку сертификата для локалки
    ssl_show_warn=False
)

try:
    # 1. Проверяем соединение
    if client.ping():
        print("✅ Соединение с OpenSearch установлено!")
    else:
        print("❌ Не удалось соединиться с OpenSearch (ping failed).")
        exit()

    # 2. Проверяем индекс
    print("\n📊 ПРОВЕРКА ДАННЫХ:")
    # Получаем список всех индексов
    indices = client.cat.indices(format="json")
    print("Существующие индексы:")
    for idx in indices:
        print(f" - {idx['index']} (документов: {idx['docs.count']})")

    # Имя вашего индекса (как в менеджере)
    TARGET_INDEX = "corporate_data" 

    # 3. Ищем данные
    if client.indices.exists(index=TARGET_INDEX):
        print(f"\n🔎 Смотрим индекс '{TARGET_INDEX}':")
        
        # Считаем документы
        count = client.count(index=TARGET_INDEX)
        print(f"Всего документов: {count['count']}")

        # Выводим примеры
        print("\n📄 ПЕРВЫЕ 3 ДОКУМЕНТА:")
        result = client.search(
            index=TARGET_INDEX,
            body={"query": {"match_all": {}}, "size": 3}
        )

        for i, hit in enumerate(result['hits']['hits'], 1):
            source = hit['_source']
            print(f"\n[{i}] {source.get('title', 'Без названия')}")
            print(f"    Категория: {source.get('category', '-')}")
            print(f"    Ссылка: {source.get('link', '-')}")
    else:
        print(f"\n⚠️ Индекс '{TARGET_INDEX}' не найден! Возможно, вы еще не загрузили данные.")

except Exception as e:
    print(f"\n❌ Ошибка подключения: {e}")
    print("Убедитесь, что Docker контейнер запущен: docker ps")