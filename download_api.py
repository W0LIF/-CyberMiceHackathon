import os
import requests
import json
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://yazzh.gate.petersburg.ru"

# Список районов Санкт-Петербурга для перебора
SPB_DISTRICTS = [
    "Адмиралтейский", "Василеостровский", "Выборгский", "Калининский",
    "Кировский", "Колпинский", "Красногвардейский", "Красносельский",
    "Кронштадтский", "Курортный", "Московский", "Невский", "Петроградский",
    "Петродворцовый", "Приморский", "Пушкинский", "Фрунзенский", "Центральный"
]

API_CATALOG = {
    "pets": [
        f"{BASE_URL}/mypets/all-category/",
        f"{BASE_URL}/mypets/posts/",
        f"{BASE_URL}/mypets/recommendations/",
        f"{BASE_URL}/mypets/animal-breeds/",
    ],
    "documents": [f"{BASE_URL}/mfc/all/"],
    # polyclinics убрали, так как требует ID
    "iparent": [
        f"{BASE_URL}/iparent/places/categoria/",
        f"{BASE_URL}/dou/available-spots/",
        f"{BASE_URL}/school/map/"
    ],
    "social": [
        f"{BASE_URL}/districts-info/district/", # Требует перебора районов
        # disconnections убрали, так как требует ID
    ]
}

# ИСПРАВЛЕНИЕ 1: Радиус уменьшен до 50 (видимо, лимит API - 100)
DEFAULT_PARAMS = {
    "location_latitude": 59.9311,
    "location_longitude": 30.3609,
    "location_radius": 50,     # Исправлено с 50000
    "limit": 1000
}

def download_all():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(root_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://yazzh.gate.petersburg.ru/'
    }

    print(f"📂 Скачиваем данные в папку: {data_dir}")

    for category, urls in API_CATALOG.items():
        print(f"\n🚀 Категория: {category}")
        
        for i, url in enumerate(urls):
            # ИСПРАВЛЕНИЕ 2: Специальная логика для районов
            if "districts-info/district" in url:
                print(f"   🔄 Перебор районов для {url}...")
                for dist_name in SPB_DISTRICTS:
                    try:
                        # Копируем параметры и добавляем район
                        params = DEFAULT_PARAMS.copy()
                        params["district_name"] = dist_name
                        
                        resp = requests.get(url, headers=headers, params=params, verify=False, timeout=10)
                        if resp.status_code == 200:
                            data = resp.json()
                            items = []
                            if isinstance(data, list): items = data
                            elif isinstance(data, dict): items = data.get("data") or data.get("results") or [data] # Иногда возвращает один объект
                            
                            if items:
                                for item in items: item['category_tag'] = category
                                
                                filename = f"api_social_district_{dist_name}.json"
                                filepath = os.path.join(data_dir, filename)
                                with open(filepath, 'w', encoding='utf-8') as f:
                                    json.dump(items, f, ensure_ascii=False, indent=2)
                                print(f"      ✅ {dist_name}: OK")
                            else:
                                print(f"      ⚠️ {dist_name}: Пусто")
                        else:
                            print(f"      ❌ {dist_name}: Ошибка {resp.status_code}")
                        
                        time.sleep(0.2) # Небольшая пауза
                    except Exception as e:
                        print(f"      ❌ {dist_name}: Exception {e}")
                continue

            # ОБЫЧНАЯ ЛОГИКА для остальных ссылок
            try:
                print(f"   Скачиваю: {url} ...", end=" ")
                resp = requests.get(url, headers=headers, params=DEFAULT_PARAMS, verify=False, timeout=15)
                
                if resp.status_code == 200:
                    data = resp.json()
                    items = []
                    if isinstance(data, list): items = data
                    elif isinstance(data, dict): items = data.get("data") or data.get("results") or []
                    
                    if not items:
                        print("⚠️ Пусто (0 записей)")
                        continue

                    for item in items:
                        item['category_tag'] = category 

                    filename = f"api_{category}_{i}.json"
                    filepath = os.path.join(data_dir, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(items, f, ensure_ascii=False, indent=2)
                    
                    print(f"✅ OK ({len(items)} шт) -> {filename}")
                
                elif resp.status_code == 422:
                    print(f"❌ Ошибка 422: {resp.text[:200]}")
                else:
                    print(f"❌ Ошибка {resp.status_code}")
            
            except Exception as e:
                print(f"❌ Exception: {e}")

if __name__ == "__main__":
    download_all()