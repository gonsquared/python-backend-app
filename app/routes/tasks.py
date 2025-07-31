from fastapi import APIRouter, HTTPException
from bson import ObjectId
from datetime import datetime
from app.database import db
from app.helpers.task_helper import serialize_task, VALID_STATUS

router = APIRouter()
tasks_collection = db["tasks"]

@router.post("/", summary="Create a new task")
async def create_task(task: dict):
    if "user" not in task or "label" not in task:
        raise HTTPException(status_code=422, detail="Fields 'user' and 'label' are required")

    if "status" not in task:
        task["status"] = "pending"

    if task["status"] not in VALID_STATUS:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {VALID_STATUS}")

    if not ObjectId.is_valid(task["user"]):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    task["user"] = ObjectId(task["user"])
    now = datetime.utcnow()
    task["createdAt"] = now
    task["updatedAt"] = now

    result = await tasks_collection.insert_one(task)
    new_task = await tasks_collection.find_one({"_id": result.inserted_id})
    return serialize_task(new_task)

@router.get("/", summary="Get all tasks")
async def get_tasks():
    tasks = await tasks_collection.find().to_list(100)
    return [serialize_task(t) for t in tasks]

@router.get("/user/{user_id}", summary="Get all tasks for a specific user")
async def get_tasks_by_user(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    tasks = await tasks_collection.find({"user": ObjectId(user_id)}).to_list(100)
    return [serialize_task(t) for t in tasks]

@router.get("/{task_id}", summary="Get a task by ID")
async def get_task(task_id: str):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    task = await tasks_collection.find_one({"_id": ObjectId(task_id)})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return serialize_task(task)

@router.put("/{task_id}", summary="Update a task by ID")
async def update_task(task_id: str, updated_task: dict):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    if "status" in updated_task and updated_task["status"] not in VALID_STATUS:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {VALID_STATUS}")

    updated_task["updatedAt"] = datetime.utcnow()
    result = await tasks_collection.update_one({"_id": ObjectId(task_id)}, {"$set": updated_task})

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")

    task = await tasks_collection.find_one({"_id": ObjectId(task_id)})
    return serialize_task(task)

@router.delete("/{task_id}", summary="Delete a task by ID")
async def delete_task(task_id: str):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    result = await tasks_collection.delete_one({"_id": ObjectId(task_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}
