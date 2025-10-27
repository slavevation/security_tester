# Цей файл знаходиться в: tester/executor.py

import requests
import time
from typing import Dict, Any, Optional

class APIExecutor:
    """
    Модуль 3: Виконавець (The Field Agent).
    Надсилає згенеровані HTTP-запити до API
    та вимірює час відповіді.
    """
    
    def __init__(self, base_url: str):
        # Нормалізуємо URL (видаляємо / в кінці, якщо є)
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        # ВАЖЛИВО: Встановимо таймаут 10 секунд.
        # Це довше, ніж атака SLEEP(5), але захистить від "зависання"
        self.default_timeout = 10 

    def execute_test(self, 
                     method: str, 
                     path: str, 
                     json_payload: Optional[Dict] = None, 
                     url_param_payload: Optional[str] = None, 
                     param_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Виконує один тест-кейс.
        """
        
        # 1. Будуємо повний URL
        full_url = self.base_url + path
        
        # 2. Підставляємо payload в URL, якщо це атака на параметр шляху
        # (напр., /items/{item_id} -> /items/1' OR 1=1)
        if param_name and url_param_payload is not None:
            full_url = self.base_url + path.replace(f"{{{param_name}}}", str(url_param_payload))

        # 3. Вимірюємо час
        start_time = time.time()
        
        try:
            # 4. Надсилаємо запит
            response = self.session.request(
                method=method,
                url=full_url,
                json=json_payload,  # 'json=' автоматично ставить правильний Content-Type
                timeout=self.default_timeout 
            )
            
            response_time = time.time() - start_time
            
            # 5. Повертаємо чистий результат
            return {
                "status_code": response.status_code,
                "body": response.text,
                "time_seconds": response_time,
                "error": None
            }

        except requests.exceptions.Timeout as e:
            # Атака тривала довше, ніж наш таймаут
            response_time = time.time() - start_time
            return {
                "status_code": 408, # Request Timeout
                "body": f"Запит перевищив таймаут {self.default_timeout}s: {e}",
                "time_seconds": response_time,
                "error": "Timeout"
            }
        
        except requests.exceptions.RequestException as e:
            # Інші помилки (напр., API не запущено)
            response_time = time.time() - start_time
            return {
                "status_code": -1, # Наш код для помилки з'єднання
                "body": str(e),
                "time_seconds": response_time,
                "error": str(e)
            }