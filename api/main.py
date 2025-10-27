from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from enum import Enum
from typing import List, Optional

app = FastAPI()

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
    global current_id
    current_id += 1

    new_item = Item(id=current_id, 
                    title=item.title, 
                    description=item.description,
                    status=item.status)

    db.append(new_item)
    return new_item

@app.get("/items/")
async def get_items():
    return db

@app.get("/items/{item_id}")
async def get_item_by_id(item_id: int):
    for item in db:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

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