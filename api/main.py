from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from enum import Enum
from typing import List, Optional
import sqlite3 
import time
from contextlib import asynccontextmanager

app = FastAPI()
DB_NAME = "vulnerable.db"

def init_db():
    """Створює нашу базу даних та таблицю, якщо їх немає."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Створюємо таблицю
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT
        )
        """)
        conn.commit()
        conn.close()
        print(f"База даних '{DB_NAME}' успішно ініціалізована.")
    except Exception as e:
        print(f"Помилка ініціалізації БД: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, який виконається 1 раз ПЕРЕД запуском
    print("🚀 Додаток запускається... Запускаю init_db().")
    init_db()
    yield
    # Код, який виконається 1 раз ПІСЛЯ зупинки (якщо потрібно)
    print("Application is shutting down...")

# --- 3. Передаємо lifespan у наш app ---
app = FastAPI(lifespan=lifespan)

class TaskStatus(str, Enum):
    TODO = "to-do"
    IN_PROGRESS = "in-progress"
    DONE = "done"

class Item(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO

class StatusUpdate(BaseModel):
    new_status: TaskStatus

db: List[Item] = []
current_id = 0

@app.get("/")
async def read_root():
    return {"message": "My First FastAPI Application!"}

@app.post("/items/", status_code=201)
async def create_item(item: Item):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Використання executescript саме по собі є ризиком
        # Хоча Pydantic нас тут рятує від SQLi в `item.title`
        sql_script = f"""
        INSERT INTO items (title, description, status) 
        VALUES ('{item.title}', '{item.description}', '{item.status.value}');
        """
        cursor.executescript(sql_script) # .executescript() може виконати SLEEP!
        
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Повертаємо створений об'єкт
        new_item = item.model_copy(update={"id": new_id})
        return new_item
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.get("/items/")
async def get_items():
    """Повертає всі елементи з БД."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Щоб отримувати dict-подібні рядки
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows] # Конвертуємо у список dict

@app.get("/items/{item_id}")
async def get_item_by_id(item_id: str): # <-- ❗️ ВРАЗЛИВІСТЬ №1: Приймаємо `str`
    """
    Шукає і повертає ОДНЕ завдання за його ID.
    Дуже вразливий до SQL Injection.
    """
    
    # ❗️ ВРАЗЛИВІСТЬ №2: Симуляція Time-based SQLi
    # Якщо payload містить 'sleep', ми чекаємо 5 секунд
    if "sleep" in item_id.lower():
        print("!!! Атака 'SLEEP' виявлена! Симулюємо затримку 5 сек... !!!")
        time.sleep(5)
    
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # ❗️ ВРАЗЛИВІСТЬ №3: Небезпечний f-string
        # Якщо item_id = "1 OR 1=1", запит стане "SELECT * ... WHERE id = 1 OR 1=1"
        sql_query = f"SELECT * FROM items WHERE id = {item_id}" 
        
        print(f"  > Виконую небезпечний SQL: {sql_query}") # (для дебагу)
        
        cursor.execute(sql_query)
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        raise HTTPException(status_code=404, detail="Item not found")
    except Exception as e:
        # Атака 'Error-based' (напр., `1'`) викличе помилку тут
        print(f"!!! SQL Помилка: {e} !!!")
        raise HTTPException(status_code=500, detail=f"SQL Error: {e}")

@app.get("/statuses")
async def get_statuses():
    return [status.value for status in TaskStatus]

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    for item in db:
        if item.id == item_id:
            db.remove(item)
            return {"status": "Item deleted successfully"}
    raise HTTPException(status_code=404, detail="Item not found")
    
@app.put("/items/{item_id}")
async def update_item(item_id: int, updated_item: Item):
    for index, item in enumerate(db):
        if item.id == item_id:
            updated_item.id = item_id
            db[index] = updated_item
            return updated_item
    raise HTTPException(status_code=404, detail="Item not found")

@app.patch("/items/{item_id}/status")
async def update_item_status(item_id: int, status: StatusUpdate):
    for item in db:
        if item.id == item_id:
            item.status = status.new_status
            return item
    raise HTTPException(status_code=404, detail="Item not found")