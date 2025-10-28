Bash:
Terminal 1:
    - source venv/Scripts/activate
    - uvicorn api.main:app --reload
Terminal 2: 
    - source venv/Scripts/activate
    - pip install -r requirements.txt
    - python run_tester.py