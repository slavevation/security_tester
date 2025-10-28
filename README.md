Bash:
Terminal 1(/my_test_api):
    - source venv/Scripts/activate
    - uvicorn api.main:app --reload
Terminal 2(/my_test_api): 
    - source venv/Scripts/activate
    - pip install -r requirements.txt
    - python run_tester.py