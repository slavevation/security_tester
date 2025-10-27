# Цей файл знаходиться в: tester/parser.py

import json
from typing import List, Dict, Any

class APIParser:
    """
    Модуль 1: Парсер.
    Відповідає за читання openapi.json та вилучення
    інформації про ендпоінти.
    """
    def __init__(self, filepath: str):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.spec = json.load(f)
        except FileNotFoundError:
            print(f"Помилка: Файл {filepath} не знайдено.")
            print("Будь ласка, запустіть API та збережіть openapi.json у корінь проєкту.")
            exit(1) # Виходимо з програми, якщо файлу немає
        except json.JSONDecodeError:
            print(f"Помилка: Файл {filepath} має неправильний JSON формат.")
            exit(1)
            
        self.endpoints = []
        self.schemas = self.spec.get('components', {}).get('schemas', {})

    def _get_schema_from_ref(self, ref_string: str) -> Dict[str, Any]:
        """
        Допоміжна функція для отримання повної схеми за її $ref посиланням.
        Приклад ref_string: '#/components/schemas/Item'
        """
        try:
            # Отримуємо назву схеми з посилання (напр., "Item")
            schema_name = ref_string.split('/')[-1]
            # Повертаємо саму схему з нашого кешу
            return self.schemas.get(schema_name, {})
        except (AttributeError, IndexError):
            return {}
        
    def parse_endpoints(self) -> List[Dict[str, Any]]:
        """
        Головний метод, який витягує всі ендпоінти.
        """
        paths = self.spec.get('paths', {}) 
        
        for path, path_info in paths.items():
            for method, method_info in path_info.items():

                request_body_schema = None
                request_body_info = method_info.get('requestBody', None)

                if request_body_info:
                    try:
                        ref = request_body_info['content']['application/json']['schema']['$ref']
                        request_body_schema = self._get_schema_from_ref(ref)
                    except (KeyError, TypeError):
                        try:
                            request_body_schema = request_body_info['content']['application/json']['schema']
                        except (KeyError, TypeError):
                            pass

                endpoint_data = {
                    "path": path,
                    "method": method.upper(),
                    "summary": method_info.get('summary', 'No summary'),
                    "parameters": method_info.get('parameters', []),
                    "requestBodySchema": request_body_schema
                }
                
                self.endpoints.append(endpoint_data)
        
        return self.endpoints