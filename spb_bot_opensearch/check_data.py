# check_data.py
from opensearchpy import OpenSearch

client = OpenSearch(
    hosts=['http://localhost:9200'],
    http_auth=('admin', 'admin123'),
    use_ssl=False
)

# 1. Проверяем индекс
print("📊 ПРОВЕРКА ДАННЫХ:")
indices = client.indices.get(index="*")
print(f"Индексы: {list(indices.keys())}")

# 2. Считаем документы
count = client.count(index="spb_help_data")
print(f"Всего документов: {count['count']}")

# 3. Выводим первые 5 документов
print("\n📄 ПЕРВЫЕ 5 ДОКУМЕНТОВ:")
result = client.search(
    index="spb_help_data",
    body={"query": {"match_all": {}}, "size": 5}
)

for i, hit in enumerate(result['hits']['hits'], 1):
    source = hit['_source']
    print(f"\n{i}. {source.get('title', 'Без названия')}")
    print(f"   Категория: {source.get('category', 'Не указана')}")
    print(f"   Ссылка: {source.get('link', 'Нет ссылки')}")
    print(f"   Контент: {source.get('content', '')[:100]}...")

# 4. Проверяем категории
print("\n📂 КАТЕГОРИИ И КОЛИЧЕСТВО:")
cats = client.search(
    index="spb_help_data",
    body={
        "aggs": {
            "categories": {
                "terms": {
                    "field": "category.keyword",
                    "size": 10
                }
            }
        },
        "size": 0
    }
)

for bucket in cats['aggregations']['categories']['buckets']:
    print(f"  - {bucket['key']}: {bucket['doc_count']} документов")