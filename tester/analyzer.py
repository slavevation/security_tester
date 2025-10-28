# Цей файл знаходиться в: tester/analyzer.py
from typing import List, Dict, Any

# Визначаємо поріг для time-based атак (напр., 4 секунди).
# Якщо атака SLEEP(5) тривала > 4 сек, ми вважаємо її успішною.
TIME_BASED_THRESHOLD = 4.0 

class APIAnalyzer:
    """
    Модуль 4: Аналізатор (The Forensic Expert).
    Аналізує результати та шукає докази вразливостей.
    """
    
    def __init__(self):
        # Тут буде наш фінальний звіт
        self.vulnerabilities = []

    def _is_time_based_sqli(self, test: Dict, result: Dict) -> bool:
        """Перевіряє на Time-based SQL Injection."""
        
        # 1. Перевіряємо, чи це взагалі була time-based атака
        desc = test.get('description', '').lower()
        if 'time-based' not in desc and 'sleep' not in desc and 'waitfor' not in desc:
            return False
        
        # 2. Перевіряємо час виконання
        if result['time_seconds'] >= TIME_BASED_THRESHOLD:
            # 3. Перевіряємо, чи сервер не повернув помилку валідації (422)
            # Успіх - це 2xx (успішно) або 5xx (помилка сервера, яку ми спричинили)
            if 200 <= result['status_code'] < 300 or result['status_code'] >= 500:
                return True
        
        return False

    def _is_error_based_sqli(self, test: Dict, result: Dict) -> bool:
        """Перевіряє на Error-based SQL Injection."""
        
        # 1. Перевіряємо, чи це була error-based атака
        desc = test.get('description', '').lower()
        if 'error-based' not in desc and 'помил' not in desc:
            return False
            
        # 2. Перевіряємо, чи сервер повернув 500 Internal Server Error
        if result['status_code'] == 500:
            # 3. (Бонус) Перевіряємо, чи тіло відповіді містить ключові слова SQL
            body = result.get('body', '').lower()
            if 'sql' in body or 'syntax' in body or 'database' in body or 'query' in body:
                return True

        return False

    def _is_reflected_xss(self, test: Dict, result: Dict) -> bool:
        """Перевіряє на Reflected XSS (дуже базово)."""
        
        # 1. Перевіряємо, чи це була XSS атака
        desc = test.get('description', '').lower()
        if 'xss' not in desc:
            return False
        
        # 2. Перевіряємо, чи payload повернувся у тілі відповіді
        payload = str(test.get('payload', ''))
        # Видаляємо пробіли і ' з payload для кращого порівняння
        payload_simple = payload.replace(" ", "").replace("'", "")
        body_simple = result.get('body', '').replace(" ", "").replace("'", "")
        
        # 3. Якщо наш "чистий" payload є в тілі відповіді і статус 200 OK
        if payload_simple in body_simple and result['status_code'] == 200:
             return True

        return False
        
    def analyze_results(self, all_results: List[Dict]) -> List[Dict]:
        """
        Головний метод. Проходить по всіх результатах і шукає вразливості.
        """
        self.vulnerabilities = []
        
        for res in all_results:
            endpoint = res['endpoint']
            test = res['test']
            result = res['result']
            
            vulnerability_found = None
            
            # --- Головна логіка детектора ---
            
            # 1. Перевірка на Time-based SQLi
            if self._is_time_based_sqli(test, result):
                vulnerability_found = {
                    "type": "Time-based SQL Injection (CRITICAL)",
                    "details": f"Атака '{test['description']}' змусила сервер 'зависнути' на {result['time_seconds']:.2f} сек. (Статус: {result['status_code']})",
                }
            
            # 2. Перевірка на Error-based SQLi
            elif self._is_error_based_sqli(test, result):
                vulnerability_found = {
                    "type": "Error-based SQL Injection (HIGH)",
                    "details": f"Атака '{test['description']}' змусила сервер повернути Статус 500 з SQL-помилкою: {result['body'][:100]}...",
                }
            
            # 3. Перевірка на Reflected XSS
            # (Ми не знайдемо її у нашому API, бо в нас немає HTML-відповідей)
            elif self._is_reflected_xss(test, result):
                 vulnerability_found = {
                    "type": "Reflected Cross-Site Scripting (MEDIUM)",
                    "details": f"Атака '{test['description']}' була відображена у відповіді сервера.",
                }
            
            # --- Кінець логіки ---
            
            # Додаємо вразливість у звіт, якщо знайшли
            if vulnerability_found:
                self.vulnerabilities.append({
                    "endpoint": f"[{endpoint['method']}] {endpoint['path']}",
                    "vulnerability": vulnerability_found,
                    "payload": test['payload']
                })
        
        return self.vulnerabilities