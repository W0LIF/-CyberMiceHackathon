# config/config.py
from datetime import timedelta

# Настройки OpenSearch
OPENSEARCH_CONFIG = {
    'hosts': ['http://localhost:9200'],
    'http_auth': ('admin', 'admin'), #Юзер и пароль одинаковы admin admin
    'use_ssl': False,
    'verify_certs': False,
    'timeout': 30,
    'max_retries': 3,
    'retry_on_timeout': True,
}

# Имя индекса
INDEX_NAME = "spb_help_data"

# Срок жизни данных (дней)
DATA_EXPIRY_DAYS = 30

# Пути к файлам
DATA_PATH = "data/"

# Категории файлов
FILE_CATEGORIES = {
    'consultant.json': 'consultant',
    'gov_spb_helper.json': 'gov_spb_helper', 
    'gu_spb_knowledge.json': 'gu_spb_knowledge',
    'gu_spb_mfc.json': 'gu_spb_mfc'
}