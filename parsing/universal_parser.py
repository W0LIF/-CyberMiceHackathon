import requests
from bs4 import BeautifulSoup
import json
import time
import csv
import os
from urllib.parse import urljoin

# Устанавливает заголовки HTTP-запросов, чтобы сайты воспринимали парсер как обычный браузер, а не как робота

class UniversalParser:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def parse_site(self, config):
        """Основной метод парсинга по конфигурации"""
        url = config['url']
        list_selectors = config['list_selectors']
        content_selectors = config.get('content_selectors', [])
        output_prefix = config['output_prefix']
        
        # Парсим список элементов
        items = self._parse_list(url, list_selectors)
        
        # Если нужно парсить контент - парсим каждый элемент
        if content_selectors and items:
            detailed_items = []
            for i, item in enumerate(items):
                if 'link' in item and item['link']:
                    print(f"Парсим контент элемента {i+1}/{len(items)}...")
                    content = self._parse_content(item['link'], content_selectors)
                    item['content'] = content
                    time.sleep(1)  # Пауза между запросами
                detailed_items.append(item)
            items = detailed_items
        
        # Сохраняем результаты
        self._save_results(items, output_prefix)
        return items
    
    # Если сайт не отвечает с первой попытки(высокая нагрузка) - делаем повторные запросы с большлой задержкой

    def _make_request_with_retry(self, url, max_retries=3):
        """Выполняет запрос с повторными попытками при таймауте"""
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.headers, timeout=30)  # Увеличили таймаут до 30 секунд
                return response
            except requests.exceptions.Timeout:
                print(f"Таймаут запроса (попытка {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)  # Ждем перед повторной попыткой
                else:
                    raise
            except requests.exceptions.RequestException as e:
                print(f"Ошибка запроса: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    raise
        return None
    
    def _parse_list(self, url, selectors):
        """Парсит список элементов с главной страницы"""
        try:
            print(f"Загружаем страницу...")
            response = self._make_request_with_retry(url)
            if not response or response.status_code != 200:
                print(f"Ошибка: статус код {getattr(response, 'status_code', 'неизвестен')} для {url}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Пробуем разные селекторы (поиск инф.) пока не найдем подходящий
            for selector_config in selectors:
                selector = selector_config['selector']
                elements = soup.select(selector)
                if elements:
                    print(f"Найдено {len(elements)} элементов с селектором: {selector}")
                    items = []
                    for element in elements:
                        item_data = {}
                        
                        # Извлекаем данные по правилам из конфигурации
                        for field, field_selector in selector_config['fields'].items():
                            try:
                                # Support formats: '@attr' (attribute on element), 'selector@attr' (select child and attribute)
                                if isinstance(field_selector, str) and '@' in field_selector:
                                    # Cases: '@attr' or 'childsel@attr'
                                    if field_selector.startswith('@'):
                                        attr_name = field_selector[1:]
                                        value = element.get(attr_name, '')
                                        item_data[field] = value.strip() if value else ''
                                    else:
                                        # split selector and attribute
                                        sel, attr_name = field_selector.split('@', 1)
                                        target_element = element.select_one(sel)
                                        if target_element:
                                            value = target_element.get(attr_name, '')
                                            item_data[field] = value.strip() if value else ''
                                        else:
                                            item_data[field] = ''
                                else:
                                    # Текст или вложенный элемент
                                    if field_selector == '':
                                        # Берем текст самого элемента
                                        value = element.get_text(strip=True)
                                        item_data[field] = value
                                    else:
                                        # Ищем вложенный элемент
                                        target_element = element.select_one(field_selector)
                                        if target_element:
                                            value = target_element.get_text(strip=True)
                                            item_data[field] = value
                                        else:
                                            item_data[field] = ''
                            except Exception as e:
                                print(f"      Ошибка при извлечении поля {field}: {e}")
                                item_data[field] = ''
                        
                        # Обрабатываем относительные ссылки
                        if 'link' in item_data and item_data['link']:
                            if not item_data['link'].startswith('http'):
                                item_data['link'] = urljoin(url, item_data['link'])
                        
                        # Проверяем, что есть хотя бы title и link
                        if item_data.get('title') and item_data.get('link'):
                            items.append(item_data)
                            print(f"Добавлен элемент: {item_data['title'][:50]}...")
                        else:
                            print(f"Пропущен элемент - нет title или link: {item_data}")
                    
                    if items:
                        return items
                    else:
                        print(f"Элементы найдены, но данные не извлечены")
            
            print("Не найдено элементов с указанными селекторами")
            return []
            
        except Exception as e:
            print(f"Ошибка при парсинге списка: {e}")
            return []
    
    # Парсинг внутренних страниц

    def _parse_content(self, url, selectors):
        """Парсит контент с внутренней страницы"""
        try:
            print(f"Загружаем контент с: {url}")
            response = self._make_request_with_retry(url)
            if not response or response.status_code != 200:
                return f"Ошибка: статус код {getattr(response, 'status_code', 'неизвестен')}"
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Пробуем разные селекторы контента
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    content = ' '.join([elem.get_text(strip=True) for elem in elements])
                    if len(content) > 50:
                        return content[:20000] # Количество символом, что мы получим в результате парсинга
            
            # Если не нашли по селекторам, берем все параграфы
            paragraphs = soup.find_all('p')
            content = ' '.join([p.get_text(strip=True) for p in paragraphs])
            return content[:20000] if content else "Контент не найден"
            
        except Exception as e:
            return f"Ошибка при загрузке контента: {str(e)}"
    
    def _save_results(self, items, prefix):
        """Сохраняет результаты в JSON и CSV"""
        if not items:
            print(f"Нет данных для сохранения")
            return
        
        # Сохраняем в папку spb_bot_opensearch/data
        json_filename = f"data/{prefix}.json"
        csv_filename = f"data/{prefix}.csv"
        
        # Создаем папку, если её нет
        os.makedirs(os.path.dirname(json_filename), exist_ok=True)
        
        # Сохраняем в JSON
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        
        # Сохраняем в CSV (если есть данные)
        if items and isinstance(items[0], dict):
            with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=items[0].keys())
                writer.writeheader()
                writer.writerows(items)
        
        print(f"Сохранено {len(items)} элементов в {json_filename} и {csv_filename}")

# Конфигурации для разных сайтов
CONFIGURATIONS = {
    'gu_spb_knowledge1': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=1',
        'output_prefix': 'gu_spb_knowledge1',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge2': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=2',
        'output_prefix': 'gu_spb_knowledge2',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge3': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=3',
        'output_prefix': 'gu_spb_knowledge3',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge4': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=4',
        'output_prefix': 'gu_spb_knowledge4',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge5': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=5',
        'output_prefix': 'gu_spb_knowledge5',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge6': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=6',
        'output_prefix': 'gu_spb_knowledge6',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge7': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=7',
        'output_prefix': 'gu_spb_knowledge7',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge8': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=8',
        'output_prefix': 'gu_spb_knowledge8',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge9': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=9',
        'output_prefix': 'gu_spb_knowledge9',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge10': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=10',
        'output_prefix': 'gu_spb_knowledge10',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge11': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=11',
        'output_prefix': 'gu_spb_knowledge11',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge12': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=12',
        'output_prefix': 'gu_spb_knowledge12',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge13': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=13',
        'output_prefix': 'gu_spb_knowledge13',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge14': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=14',
        'output_prefix': 'gu_spb_knowledge14',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge15': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=15',
        'output_prefix': 'gu_spb_knowledge15',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge16': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=16',
        'output_prefix': 'gu_spb_knowledge16',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge17': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=17',
        'output_prefix': 'gu_spb_knowledge17',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge18': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=18',
        'output_prefix': 'gu_spb_knowledge18',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge19': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=19',
        'output_prefix': 'gu_spb_knowledge19',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge20': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=20',
        'output_prefix': 'gu_spb_knowledge20',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    'gu_spb_knowledge21': {
        'url': 'https://gu.spb.ru/knowledge-base/?PAGEN_1=21',
        'output_prefix': 'gu_spb_knowledge21',    # Префиксы для файлов
        'list_selectors': [     # Лист селекторов
            {
                'selector': 'div.element-card a.ambient__link-ctrl', # CSS селектор
                'fields': {    # Какие поля извлекать 
                    'title': '',  # текст самой ссылки. Пример: "Как получить паспорт" (текст ссылки)
                    'link': '@href'  # атрибут href, берем атрибуты элемента Пример: "/knowledge/123" (атрибут href)
                }
            },
            {
                'selector': '.element-card .title-usual a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.ambient__link-ctrl',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.element-card a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.text-container',
            '.paragraph-base', 
            '.box._mode-usual',
            'main',
            '.content',
            'article'
        ]
    },
    
    'gu_spb_mfc': {
        'url': 'https://gu.spb.ru/mfc/life_situations/',
        'output_prefix': 'gu_spb_mfc',
        'list_selectors': [
            {
                'selector': 'div.life-situation-item a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.life-situation-item a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a[href*="/life_situations/"]',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.life-situation-item',
                'fields': {
                    'title': 'a',  # текст внутри ссылки
                    'link': 'a@href'  # href ссылки
                }
            }
        ],
        'content_selectors': [
            '.content-block',
            '.text-container',
            'main',
            '.life-situation-content',
            'article'
        ]
    },
    
    'gov_spb_helper': {
        'url': 'https://www.gov.spb.ru/helper/',
        'output_prefix': 'gov_spb_helper', 
        'list_selectors': [
            {
                'selector': '.col-lg-4 h2 a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.unstyled-list a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.content a[href^="/helper/"]',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.text-body',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.content-block',
            '.text-block',
            'main',
            '.content',
            'article'
        ]
    },
    
    'consultant': {
        'url': 'https://www.consultant.ru/',
        'output_prefix': 'consultant',
        'list_selectors': [
            {
                'selector': 'a[href*="/document/"]',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': '.news-item a',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            },
            {
                'selector': 'a.news-item',
                'fields': {
                    'title': '',
                    'link': '@href'
                }
            }
        ],
        'content_selectors': [
            '.document-page',
            '.text',
            'main',
            '.content',
            'article'
        ]
    }
}

def main():
    parser = UniversalParser()
    
    # Парсим все сайты из конфигурации
    for site_name, config in CONFIGURATIONS.items():
        print(f"Парсим сайт: {site_name}")
        print(f"URL: {config['url']}")
        
        try:
            items = parser.parse_site(config)
            print(f"Итог: получено {len(items)} элементов\n")
        except Exception as e:
            print(f"КРИТИЧЕСКАЯ ОШИБКА при парсинге {site_name}: {e}\n")
        
        time.sleep(3)  # Пауза между сайтами
    
    print("Парсинг всех сайтов завершен")

if __name__ == "__main__":
    main()