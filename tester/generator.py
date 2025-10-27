import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

class AttackGenerator:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            print("Помилка: Не знайдено GOOGLE_API_KEY у .env файлі.")
            print("Будь ласка, створіть .env та додайте ключ з Google AI Studio.")
            exit(1)
        
        try:
            genai.configure(api_key=api_key)
            #Ініціалізуємо модель
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            print("Модель Gemini 2.5 Flash успішно ініціалізована.")
        except Exception as e:
            print(f"Помилка ініціалізації Gemini: {e}")
            exit(1)

    def _create_prompt(self, endpoint_data: Dict[str, Any]) -> Optional[str]:
        """
        Приватний метод для створення "промпту" (запиту) до LLM.
        ОНОВЛЕНА ВЕРСІЯ: Забороняє деструктивні атаки.
        """
        method = endpoint_data['method']
        path = endpoint_data['path']
        schema = endpoint_data.get('requestBodySchema')
        params = endpoint_data.get('parameters')

        # Базовий шаблон промпту
        base_prompt = (
            "Ти — етичний експерт з тестування безпеки API (пентестер)."
            "Твоє завдання — згенерувати 5 прикладів тест-кейсів для *виявлення* вразливостей на"
            f"ендпоінті: [{method}] {path}\n"
            "Сконцентруйся на не-деструктивних атаках: XSS (Cross-Site Scripting) та SQL Injection (тільки 'read-only' та 'time-based', наприклад, `SLEEP` або `' OR 1=1`).\n"
            "**КАТЕГОРИЧНО ЗАБОРОНЕНО** генерувати деструктивні команди, що змінюють дані, такі як `DROP TABLE`, `DELETE FROM`, `UPDATE`, `INSERT INTO`.\n"
        )

        # 1. Якщо є тіло запиту (POST, PUT, PATCH)
        if schema:
            schema_json = json.dumps(schema, indent=4)
            base_prompt += (
                f"Ендпоінт очікує тіло запиту у форматі JSON, що відповідає цій схемі:\n"
                f"```json\n{schema_json}\n```\n"
                "Знайди всі поля типу 'string' у схемі та згенеруй JSON-об'єкти для 'payload', "
                "які намагаються експлуатувати XSS або не-деструктивні SQLi у цих полях.\n"
                "Формат відповіді: JSON-список об'єктів. Кожен об'єкт: "
                "{'description': 'Опис атаки (напр., XSS в полі title)', 'payload': {...сам JSON...}}\n"
            )
            return base_prompt

        # 2. Якщо є параметри в URL (GET, DELETE)
        if params:
            param_names = [p.get('name') for p in params if p.get('in') == 'path']
            if not param_names:
                return None # Немає параметрів для атаки
                
            base_prompt += (
                f"Ендпоінт приймає параметри в URL: {param_names}.\n"
                "Згенеруй рядкові значення для 'payload', "
                "які намагаються експлуатувати не-деструктивні SQL Injection у цих параметрах.\n"
                "Формат відповіді: JSON-список об'єктів. Кожен об'єкт: "
                "{'description': 'Опис атаки (напр., Time-based SQLi в item_id)', 'payload': '...сам рядок для параметра...'}\n"
            )
            return base_prompt

        # 3. Якщо нічого тестувати (напр. GET /)
        return None
    
    def _parse_llm_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Приватний метод для очистки та парсингу відповіді від LLM.
        LLM люблять загортати JSON у ```json ... ``` та додавати текст до/після.
        """
        try:
            # 1. Знаходимо початок та кінець JSON-блоку
            #    find() знайде перший ```json, навіть якщо перед ним є текст
            start_index = response_text.find("```json")
            end_index = response_text.rfind("```") # rfind() знайде останній ```

            if start_index != -1 and end_index != -1 and end_index > start_index:
                # 2. Вирізаємо чистий JSON-текст
                # +7 щоб пропустити "```json\n"
                json_text = response_text[start_index + 7 : end_index].strip()
            else:
                # Якщо ```json не знайдено, можливо, LLM повернув *тільки* JSON
                # (або щось зовсім інше). Спробуємо просто очистити рядок.
                json_text = response_text.strip()

            # 3. Парсимо JSON
            test_cases = json.loads(json_text)
            if isinstance(test_cases, list):
                return test_cases
            else:
                print(f"  > Помилка парсингу: LLM повернув не список. Відповідь: {json_text}")
                return []
        
        except json.JSONDecodeError as e:
            # Цей except спрацює, якщо json_text все ще містить вступний текст
            print(f"  > Помилка парсингу: LLM повернув невалідний JSON. Помилка: {e}")
            print(f"  > Отримана відповідь (оригінал): {response_text}")
            return []
        
    def generate_test_cases_for_endpoint(self, endpoint_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Публічний метод для генерації тест-кейсів для одного ендпоінта.
        """
        #Створюємо промпт
        prompt = self._create_prompt(endpoint_data)
        
        if prompt is None:
            # Для цього ендпоінта немає чого тестувати
            return []
        
        #Відправляємо запит до Gemini
        try:
            response = self.model.generate_content(prompt)
            
            # 3. Парсимо відповідь
            test_cases = self._parse_llm_response(response.text)
            return test_cases
            
        except Exception as e:
            print(f"  > Помилка під час запиту до Gemini API: {e}")
            return []