from tester.parser import APIParser
from tester.generator import AttackGenerator
from tester.executor import APIExecutor
from tester.analyzer import APIAnalyzer
import json
import os                 
from datetime import datetime 

OPENAPI_FILE_PATH = "openapi.json"
BASE_URL = "http://127.0.0.1:8000" 
RESULTS_DIR = "results"          

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True) # Створюємо папку, якщо її немає
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_filename = f"test_report_{timestamp}.txt"
    report_filepath = os.path.join(RESULTS_DIR, report_filename)
    
    report_lines = [] # Тут будемо збирати весь наш вивід
    
    # Створимо маленьку функцію, щоб одночасно друкувати і зберігати
    def log(message):
        print(message)
        report_lines.append(message)

    log("--- [Запуск Тестувальника Безпеки API] ---")
    log(f"Час запуску: {timestamp}")
    
    # --- КРОК 1: ПАРСИНГ ---
    log(f"\n[Крок 1] Аналіз файлу {OPENAPI_FILE_PATH}...")
    parser = APIParser(filepath=OPENAPI_FILE_PATH)
    all_endpoints = parser.parse_endpoints()
    log(f"✅ Успішно проаналізовано! Знайдено {len(all_endpoints)} ендпоінтів.")

    # --- КРОК 2: ГЕНЕРАЦІЯ АТАК (LLM) ---
    log("\n[Крок 2] Генерація тест-кейсів (LLM)...")
    generator = AttackGenerator()
    all_test_plans = [] 
    
    for ep in all_endpoints:
        log(f"  > Генерую тести для [{ep['method']}] {ep['path']}...")
        test_cases = generator.generate_test_cases_for_endpoint(ep)
        if test_cases:
            all_test_plans.append({"endpoint": ep, "tests": test_cases})
    log(f"✅ Згенеровано плани атак для {len(all_test_plans)} ендпоінтів.")


    # --- КРОК 3: ВИКОНАННЯ АТАК ---
    log("\n[Крок 3] Виконання атак...")
    executor = APIExecutor(base_url=BASE_URL)
    all_results = [] 
    
    for plan in all_test_plans:
        ep = plan['endpoint']
        log(f"\n  > Тестую [{ep['method']}] {ep['path']}...")
        
        for test in plan['tests']:
            json_payload = None
            url_param_payload = None
            param_name = None
            if ep['requestBodySchema']:
                json_payload = test['payload']
            elif ep['parameters']:
                url_param_payload = str(test['payload'])
                param_name = ep['parameters'][0]['name'] 
            
            result = executor.execute_test(
                method=ep['method'],
                path=ep['path'],
                json_payload=json_payload,
                url_param_payload=url_param_payload,
                param_name=param_name
            )
            
            log(f"    - Атака: {test['description'][:70]}...")
            log(f"    - > РЕЗУЛЬТАТ: Статус {result['status_code']} за {result['time_seconds']:.2f} сек.")
            if result['error']:
                log(f"    - > ❗️ ПОМИЛКА: {result['body']}") 
            
            all_results.append({ "endpoint": ep, "test": test, "result": result })

    # --- КРОК 4: АНАЛІЗ РЕЗУЛЬТАТІВ ---
    log("\n" + "="*50)
    log("--- 🏁 ФІНАЛЬНИЙ ЗВІТ ПРО ВРАЗЛИВОСТІ ---")
    log("="*50)
    
    analyzer = APIAnalyzer()
    vulnerabilities = analyzer.analyze_results(all_results)
    
    if not vulnerabilities:
        log("\n✅ Вітаємо! Жодних критичних вразливостей не знайдено.")
        log("   Ваша валідація типів (статуси 422) та бізнес-логіка (статуси 201)")
        log("   коректно обробили всі атаки.")
        log("\n   Пояснення:")
        log("   - Статус 422 (Unprocessable Entity): Ваш API захищений валідацією. Він відхилив")
        log("     шкідливий ввід (напр., рядок замість числа) *до* того, як він потрапив до логіки.")
        log("   - Статус 201 (Created) за 0.0 сек: Ваш API зберіг шкідливий рядок (напр., SQLi)")
        log("     як звичайний текст, але *не виконав* його. Це також безпечна поведінка.")
    else:
        log(f"\n🚨 УВАГА! Знайдено {len(vulnerabilities)} вразливостей:")
        for i, vuln in enumerate(vulnerabilities):
            log(f"\n--- Вразливість #{i+1} ---")
            log(f"  Тип      : {vuln['vulnerability']['type']}")
            log(f"  Ендпоінт : {vuln['endpoint']}")
            log(f"  Деталі   : {vuln['vulnerability']['details']}")
            log(f"  Payload  : {json.dumps(vuln['payload'])}")
    
    log("\n--- [Тестування завершено] ---")

    # --- 5. Зберігаємо звіт у файл ---
    try:
        with open(report_filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(report_lines))
        print("\n" + "="*50)
        print(f"✅ Звіт успішно збережено у файл:")
        print(f"   {report_filepath}")
        print("="*50)
    except Exception as e:
        print(f"\n❗️ Помилка під час збереження звіту у файл: {e}")


if __name__ == "__main__":
    main()