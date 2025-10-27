from tester.generator import AttackGenerator
from tester.parser import APIParser
from tester.executor import APIExecutor
import json 

OPENAPI_FILE_PATH = "openapi.json"
BASE_URL = "http://127.0.0.1:8000"

def main():
    print("--- [Запуск Тестувальника Безпеки API] ---")
    
    print(f"\n[Крок 1] Аналіз файлу {OPENAPI_FILE_PATH}...")
    
    parser = APIParser(filepath=OPENAPI_FILE_PATH)
    all_endpoints = parser.parse_endpoints()
    
    print(f"✅ Успішно проаналізовано! Знайдено {len(all_endpoints)} ендпоінтів.")
    print("-" * 30)
    
    for ep in all_endpoints:
        print(f"  [{ep['method']}] {ep['path']}")
        print(f"    Summary: {ep['summary']}")
        
        if ep['parameters']:
            param_names = [param['name'] for param in ep['parameters']]
            print(f"    URL Parameters : {param_names}")

        if ep['requestBodySchema']:
            print(f"    Body Schema    :")
            
            schema_pretty = json.dumps(ep['requestBodySchema'], indent=8)
            print(f"{schema_pretty}")
                
        print("-" * 20) 

    print("\n[Крок 2] Генерація тест-кейсів (LLM)...")

    generator = AttackGenerator()
    all_test_plans = []

    for ep in all_endpoints:
        print(f"  > Генерую тести для [{ep['method']}] {ep['path']}...")
        
        # 3. Для кожного ендпоінта просимо згенерувати тести
        test_cases = generator.generate_test_cases_for_endpoint(ep)
        
        if test_cases:
            print(f"    ... ✅ згенеровано {len(test_cases)} тест-кейсів.")
            # 4. Зберігаємо план атаки
            all_test_plans.append({
                "endpoint": ep,
                "tests": test_cases
            })
        else:
            print("    ... ⚪️ тест-кейси не потрібні.")

    # --- Виведемо згенеровані тести для перевірки ---
    print("\n--- [Згенеровані Плани Атак] ---")
    for plan in all_test_plans:
        ep = plan['endpoint']
        print(f"\n📍 Ендпоінт: [{ep['method']}] {ep['path']}")
        for test in plan['tests']:
            print(f"  - Атака: {test['description']}")
            print(f"  - Payload: {json.dumps(test['payload'])}")
    
    print("\n[Крок 3] Виконання атак...")
    
    executor = APIExecutor(base_url=BASE_URL)
    all_results = [] 

    for plan in all_test_plans:
        ep = plan['endpoint']
        method = ep['method']
        path = ep['path']
        
        print(f"\n  > Тестую [{method}] {path}...")
        
        for test in plan['tests']:
            payload = test['payload']
            json_payload = None
            url_param_payload = None
            param_name = None

            if ep['requestBodySchema']:
                # Payload йде в тіло JSON
                json_payload = payload
            elif ep['parameters']:
                # Payload йде в URL
                url_param_payload = str(payload)
                # (Припускаємо, що параметр один, що вірно для нашого API)
                param_name = ep['parameters'][0]['name'] 
            
            # 4. ВИКОНУЄМО ТЕСТ!
            result = executor.execute_test(
                method=method,
                path=path,
                json_payload=json_payload,
                url_param_payload=url_param_payload,
                param_name=param_name
            )
            
            # 5. Друкуємо короткий звіт
            print(f"    - Атака: {test['description']}")
            print(f"    - > РЕЗУЛЬТАТ: Статус {result['status_code']} за {result['time_seconds']:.2f} сек.")
            
            # Зберігаємо все для аналізу
            all_results.append({
                "endpoint": ep,
                "test": test,
                "result": result
            })

if __name__ == "__main__":
    main()