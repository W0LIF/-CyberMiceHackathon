import os
import json
import logging
import sys
from datetime import datetime, timedelta
from opensearchpy import OpenSearch, helpers

# Конфигурируем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('opensearch.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)
# Убираем шум от самой библиотеки
logging.getLogger('opensearchpy').setLevel(logging.ERROR)

class OpenSearchManager:
    
    def __init__(self):
        self.host = 'localhost'
        self.port = 9200
        self.index_name = "corporate_data"
        self.metadata_file = os.path.join(os.path.dirname(__file__), 'index_metadata.json')

        # Настройки подключения
        self.client = OpenSearch(
            hosts=[{'host': self.host, 'port': self.port}],
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False
        )
        
        # Пути к данным
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_file_dir)
        self.data_folder = os.path.join(project_root, "data")
        
        print(f"OpenSearchManager ищет данные в: {self.data_folder}")

    def setup_index(self):
        """Создает индекс с правильным маппингом"""
        index_body = {
            "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 0}},
            "mappings": {
                "properties": {
                    "title": {"type": "text", "analyzer": "standard"},
                    "content": {"type": "text", "analyzer": "standard"},
                    "address": {"type": "text", "analyzer": "standard"},
                    "phone": {"type": "text"},
                    "category": {"type": "keyword"},
                    "link": {"type": "keyword"},
                    "source_file": {"type": "keyword"},
                    
                    # district = keyword (важно для точного фильтра)
                    "district": {"type": "keyword"}, 
                    
                    "kind": {"type": "keyword"}
                }
            }
        }
        if not self.client.indices.exists(index=self.index_name):
            self.client.indices.create(index=self.index_name, body=index_body)
            print(f"Индекс '{self.index_name}' создан.")

    def load_all_data(self):
        """Читает JSON файлы и загружает в базу"""
        if not os.path.exists(self.data_folder):
            print(f"Ошибка: Папка {self.data_folder} не найдена!")
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
                        doc = self._prepare_doc(item, filename)
                        if doc:
                            docs_to_upload.append(doc)
            except Exception as e:
                print(f"Ошибка в файле {filename}: {e}")

        if docs_to_upload:
            # Пересоздаем индекс, чтобы данные были чистыми
            if self.client.indices.exists(index=self.index_name):
                self.client.indices.delete(index=self.index_name)
            self.setup_index()

            success, failed = helpers.bulk(self.client, docs_to_upload)
            print(f"Успешно загружено: {success} документов.")
        
        self.client.indices.refresh(index=self.index_name)

    def _prepare_doc(self, item, filename):
        """Подготовка документа с авто-определением района из названия."""
        actual_item = item
        if 'place' in item and isinstance(item['place'], dict):
            actual_item = item['place']

        title = actual_item.get('name') or actual_item.get('title') or actual_item.get('short_name')
        if not title: 
            title = f"Объект без названия ({actual_item.get('kind', '')})"

        description = actual_item.get('description') or ""
        extra_info = []
        if actual_item.get('profile'): 
            extra_info.append(f"Профиль: {', '.join(actual_item['profile'])}")
        
        full_content = f"{description} {' '.join(extra_info)}"
        
        # === ЛОГИКА ОПРЕДЕЛЕНИЯ РАЙОНА ===
        # 1. Сначала пробуем взять явное поле (как у школ)
        raw_district = actual_item.get('district', '')
        district = ""

        if raw_district:
            district = str(raw_district).strip().capitalize()
        else:
            # 2. Если поля нет (как у МФЦ), пытаемся найти район в названии (title)
            # Словарь: "корень слова" -> "Нормальное Название"
            district_map = {
                "адмиралтейск": "Адмиралтейский",
                "василеостровск": "Василеостровский",
                "выборгск": "Выборгский",
                "калининск": "Калининский",
                "кировск": "Кировский",
                "колпинск": "Колпинский",
                "красногвардейск": "Красногвардейский",
                "красносельск": "Красносельский",
                "кронштадтск": "Кронштадтский",
                "курортн": "Курортный",
                "московск": "Московский",
                "невск": "Невский",
                "петроградск": "Петроградский",
                "петродворцов": "Петродворцовый",
                "приморск": "Приморский",
                "пушкинск": "Пушкинский",
                "фрунзенск": "Фрунзенский",
                "центральн": "Центральный"
            }
            
            title_lower = str(title).lower()
            for root, name in district_map.items():
                if root in title_lower:
                    district = name
                    break
        # =================================

        return {
            "_index": self.index_name,
            "_source": {
                "title": str(title),
                "content": str(full_content),
                "address": str(actual_item.get('address', '')),
                "phone": str(actual_item.get('phone', '')),
                "category": item.get('category_tag', 'general'),
                "link": actual_item.get('link', '#'),
                "source_file": filename,
                "district": district, # Теперь здесь будет "Василеостровский" даже для МФЦ
                "kind": actual_item.get('kind', ''),
                "profile": actual_item.get('profile', []),
                "subject": actual_item.get('subject', [])
            }
        }

    def search(self, query_text, source=None, district=None, size=5):
        """
        Умный поиск с фильтрами.
        """
        must_clauses = []
        
        # === ВАЖНОЕ ИЗМЕНЕНИЕ ===
        # Если текста нет или он пустой — используем match_all (вернуть всё)
        if not query_text or not query_text.strip():
            must_clauses.append({"match_all": {}})
        else:
            must_clauses.append({
                "multi_match": {
                    "query": query_text,
                    "fields": ["title^3", "address^2", "content", "district"],
                    "fuzziness": "AUTO"
                }
            })
        # ========================
        
        filter_clauses = []
        
        # Фильтр по файлу
        if source:
            filter_clauses.append({"term": {"source_file": source}})
            
        # Фильтр по району (точный)
        if district:
             filter_clauses.append({"term": {"district": district}})

        search_body = {
            "size": size,
            "query": {
                "bool": {
                    "must": must_clauses,
                    "filter": filter_clauses
                }
            }
        }
        
        try:
            response = self.client.search(index=self.index_name, body=search_body)
            return response['hits']['hits']
        except Exception as e:
            print(f"Ошибка поиска OpenSearch: {e}")
            return []

    # --- Методы проверки и обновления ---
    def is_index_expired(self):
        if not os.path.exists(self.metadata_file): return True
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                last_update = datetime.fromisoformat(metadata.get('last_update', '2000-01-01'))
                return datetime.now() - last_update > timedelta(days=30)
        except Exception: return True

    def is_index_empty(self):
        try:
            if not self.client.indices.exists(index=self.index_name):
                return True
            count = self.client.count(index=self.index_name)
            return count['count'] == 0
        except Exception: return True

    def update_metadata(self):
        metadata = {'last_update': datetime.now().isoformat()}
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f)

    def ensure_data_loaded(self):
        """Проверяет индекс при старте"""
        try:
            if not self.client.ping():
                print("Не удалось подключиться к OpenSearch (проверьте Docker)")
                return False
                
            if self.is_index_empty():
                print("Индекс пуст, начинаю загрузку данных...")
                self.load_all_data()
                self.update_metadata()
                return True
                
            if self.is_index_expired():
                print("Данные устарели (>30 дней), обновляю...")
                self.load_all_data()
                self.update_metadata()
                return True
                
            print(f"Данные в OpenSearch актуальны.")
            return False
        except Exception as e:
            print(f"Ошибка при проверке данных: {e}")
            return False