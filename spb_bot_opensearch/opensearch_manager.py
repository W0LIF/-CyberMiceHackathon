import os
import json
import logging
from opensearchpy import OpenSearch, helpers

logger = logging.getLogger(__name__)

class OpenSearchManager:
    def __init__(self):
        self.host = 'localhost'
        self.port = 9200
        self.auth = ('admin', 'admin')
        self.index_name = "corporate_data"

        self.client = OpenSearch(
            hosts=[{'host': self.host, 'port': self.port}],
            http_auth=self.auth,
            use_ssl=True,
            verify_certs=False,
            ssl_show_warn=False
        )
        
        # === ИЗМЕНЕНИЕ: Ищем папку data в КОРНЕ проекта ===
        # 1. Папка, где лежит этот файл (spb_bot_opensearch)
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        # 2. Родительская папка (корень проекта)
        project_root = os.path.dirname(current_file_dir)
        # 3. Папка data в корне
        self.data_folder = os.path.join(project_root, "data")
        
        # Для отладки (чтобы вы видели, где он ищет)
        # print(f"OpenSearchManager ищет данные в: {self.data_folder}")

    def setup_index(self):
        index_body = {
            "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 0}},
            "mappings": {
                "properties": {
                    "title": {"type": "text", "analyzer": "standard"},
                    "content": {"type": "text", "analyzer": "standard"},
                    "address": {"type": "text", "analyzer": "standard"},
                    "phone": {"type": "text"},
                    "category": {"type": "keyword"},
                    "link": {"type": "keyword"}
                }
            }
        }
        if not self.client.indices.exists(index=self.index_name):
            self.client.indices.create(index=self.index_name, body=index_body)
            logger.info(f"Индекс '{self.index_name}' создан.")

    def load_all_data(self):
        """Читает ВСЕ json файлы из папки data и грузит в базу"""
        if not os.path.exists(self.data_folder):
            logger.error(f"Папка {self.data_folder} не найдена!")
            return

        files = [f for f in os.listdir(self.data_folder) if f.endswith('.json')]
        docs_to_upload = []

        print(f"Найдено файлов для загрузки: {len(files)} в папке {self.data_folder}")

        for filename in files:
            file_path = os.path.join(self.data_folder, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    items = data if isinstance(data, list) else [data]
                    
                    for item in items:
                        doc = self._prepare_doc(item)
                        if doc:
                            docs_to_upload.append(doc)
            except Exception as e:
                logger.error(f"Ошибка в файле {filename}: {e}")

        if docs_to_upload:
            # Очищаем старый индекс перед полной загрузкой
            if self.client.indices.exists(index=self.index_name):
                self.client.indices.delete(index=self.index_name)
            self.setup_index()

            success, failed = helpers.bulk(self.client, docs_to_upload)
            logger.info(f"✅ Успешно загружено: {success} документов.")
        
        self.client.indices.refresh(index=self.index_name)

    def _prepare_doc(self, item):
        actual_item = item
        if 'place' in item and isinstance(item['place'], dict):
            actual_item = item['place']

        title = actual_item.get('name') or actual_item.get('title') or actual_item.get('short_name')
        if not title: return None

        address = actual_item.get('address') or actual_item.get('location') or ""
        if isinstance(address, dict): address = address.get('address', '')

        content = actual_item.get('description') or actual_item.get('text') or actual_item.get('content') or ""
        category = item.get('category_tag') or actual_item.get('category') or 'general'

        return {
            "_index": self.index_name,
            "_source": {
                "title": str(title),
                "content": str(content),
                "address": str(address),
                "phone": str(actual_item.get('phone', '')),
                "category": category,
                "link": actual_item.get('link') or actual_item.get('url') or "#"
            }
        }

    def search(self, query_text, size=5):
        search_body = {
            "size": size,
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": ["title^3", "address^2", "content"],
                    "fuzziness": "AUTO"
                }
            }
        }
        try:
            response = self.client.search(index=self.index_name, body=search_body)
            return response['hits']['hits']
        except Exception:
            return []