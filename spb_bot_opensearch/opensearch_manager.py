import os
import json
import logging
from opensearchpy import OpenSearch, helpers

# Настройка логгера (используем тот же формат, что и в main.py)
logger = logging.getLogger(__name__)

class OpenSearchManager:
    def __init__(self):
        # 1. Настройки подключения (обычно берутся из переменных окружения)
        # Если у вас OpenSearch запущен локально без SSL, настройки могут отличаться
        self.host = 'localhost'
        self.port = 9200
        self.auth = ('admin', 'admin') # Стандартные логин/пароль для OpenSearch
        self.index_name = "corporate_data" # Имя индекса (базы)

        # Инициализация клиента
        self.client = OpenSearch(
            hosts=[{'host': self.host, 'port': self.port}],
            http_auth=self.auth,
            use_ssl=True,           # Включите False, если у вас локальная версия без HTTPS
            verify_certs=False,     # Отключаем проверку сертификатов для локальной разработки
            ssl_show_warn=False
        )
        
        # Путь к папке с JSON файлами
        self.data_folder = "data" 

    def setup_index(self):
        """Создает индекс с правильной схемой данных, если он не существует"""
        
        # Схема индекса (маппинг)
        index_body = {
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0
                }
            },
            "mappings": {
                "properties": {
                    "title": {"type": "text", "analyzer": "standard"},
                    "content": {"type": "text", "analyzer": "standard"},
                    "link": {"type": "keyword"},
                    "category": {"type": "keyword"}, # keyword нужен для точной агрегации (статистики)
                    "created_at": {"type": "date"}
                }
            }
        }

        # Проверяем, существует ли индекс
        if not self.client.indices.exists(index=self.index_name):
            self.client.indices.create(index=self.index_name, body=index_body)
            logger.info(f"Индекс '{self.index_name}' успешно создан.")
        else:
            logger.info(f"Индекс '{self.index_name}' уже существует.")

    def load_all_data(self):
        """Читает JSON файлы из папки и загружает их в OpenSearch"""
        
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            logger.warning(f"Папка {self.data_folder} не найдена. Создана пустая папка.")
            return

        files = [f for f in os.listdir(self.data_folder) if f.endswith('.json')]
        if not files:
            logger.warning("JSON файлы не найдены.")
            return

        docs_to_upload = []

        for filename in files:
            file_path = os.path.join(self.data_folder, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Если в файле список объектов
                    if isinstance(data, list):
                        for item in data:
                            docs_to_upload.append(self._prepare_doc(item))
                    # Если в файле один объект
                    elif isinstance(data, dict):
                        docs_to_upload.append(self._prepare_doc(data))
                        
            except Exception as e:
                logger.error(f"Ошибка при чтении файла {filename}: {e}")

        if docs_to_upload:
            # Используем bulk helper для быстрой загрузки
            success, failed = helpers.bulk(self.client, docs_to_upload)
            logger.info(f"Загружено документов: {success}, Ошибок: {failed}")
        
        # Обновляем индекс, чтобы данные стали доступны для поиска сразу
        self.client.indices.refresh(index=self.index_name)

    def _prepare_doc(self, source_data):
        """Вспомогательный метод для форматирования данных под bulk API"""
        return {
            "_index": self.index_name,
            "_source": {
                "title": source_data.get("title", "Без заголовка"),
                "content": source_data.get("content", ""),
                "category": source_data.get("category", "Uncategorized"),
                "link": source_data.get("link", "#"),
                "created_at": source_data.get("created_at", None)
            }
        }

    def cleanup_old_data(self):
        """
        Удаляет устаревшие данные.
        Здесь пример удаления документов, у которых category = 'deprecated'.
        """
        query = {
            "query": {
                "term": {
                    "category": "deprecated"
                }
            }
        }
        try:
            response = self.client.delete_by_query(index=self.index_name, body=query)
            logger.info(f"Удалено устаревших документов: {response.get('deleted', 0)}")
        except Exception as e:
            logger.error(f"Ошибка очистки данных: {e}")

    def get_statistics(self):
        """Возвращает общее количество и разбивку по категориям"""
        
        # Агрегационный запрос
        body = {
            "size": 0, # Нам не нужны сами документы, только цифры
            "aggs": {
                "categories_count": {
                    "terms": {
                        "field": "category",
                        "size": 10
                    }
                }
            }
        }
        
        res = self.client.search(index=self.index_name, body=body)
        
        total = res['hits']['total']['value']
        buckets = res['aggregations']['categories_count']['buckets']
        
        categories_stats = {b['key']: b['doc_count'] for b in buckets}
        
        return {
            "total_documents": total,
            "categories": categories_stats
        }

    def search(self, query_text, size=5):
        """Полнотекстовый поиск по заголовку и содержимому"""
        
        search_body = {
            "size": size,
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": ["title^2", "content"], # Заголовок в 2 раза важнее контента
                    "fuzziness": "AUTO" # Прощает опечатки
                }
            }
        }
        
        try:
            response = self.client.search(index=self.index_name, body=search_body)
            return response['hits']['hits']
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return []