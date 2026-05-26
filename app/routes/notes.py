from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.database import db
from app.dependencies.auth import get_current_user
from app.helpers.user_helper import get_user_role
from app.models.note_model import Note, UpdateNote

router = APIRouter()
notes_collection = db["notes"]


def model_to_dict(model):
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()


def user_is_admin(user) -> bool:
    return get_user_role(user) == "admin"


def note_belongs_to_user(note, user) -> bool:
    return note.get("user") == str(user.get("_id"))


def require_note_access(note, current_user):
    if user_is_admin(current_user) or note_belongs_to_user(note, current_user):
        return

    raise HTTPException(status_code=403, detail="You can only manage your own notes")


def serialize_note(note):
    return {
        "id": str(note["_id"]),
        "title": note["title"],
        "contents": note["contents"],
        "status": note.get("status", "not published"),
        "user": note["user"],
        "createdAt": note.get("createdAt"),
        "updatedAt": note.get("updatedAt"),
    }


def validate_note_id(note_id: str):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note ID format")


def validate_user_id(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")


async def find_note_or_404(note_id: str):
    validate_note_id(note_id)
    note = await notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("/", summary="Create a new note")
async def create_note(note: Note, current_user=Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    note_dict = model_to_dict(note)
    note_dict["user"] = str(current_user["_id"])
    note_dict["createdAt"] = now
    note_dict["updatedAt"] = now

    result = await notes_collection.insert_one(note_dict.copy())
    return serialize_note({"_id": result.inserted_id, **note_dict})


@router.get("/", summary="Get notes")
async def get_notes(current_user=Depends(get_current_user)):
    query = {} if user_is_admin(current_user) else {"user": str(current_user["_id"])}
    notes = await notes_collection.find(query).to_list(100)
    return [serialize_note(note) for note in notes]


@router.get("/by-user/{user_id}", summary="Get notes by user")
async def get_notes_by_user(user_id: str, current_user=Depends(get_current_user)):
    validate_user_id(user_id)
    if not user_is_admin(current_user) and str(current_user.get("_id")) != user_id:
        raise HTTPException(status_code=403, detail="You can only manage your own notes")

    notes = await notes_collection.find({"user": user_id}).to_list(100)
    return [serialize_note(note) for note in notes]


@router.get("/{note_id}", summary="Get note by ID")
async def get_note_by_id(note_id: str, current_user=Depends(get_current_user)):
    note = await find_note_or_404(note_id)
    require_note_access(note, current_user)
    return serialize_note(note)


@router.put("/{note_id}", summary="Update note by ID")
async def update_note(
    note_id: str, updated_note: UpdateNote, current_user=Depends(get_current_user)
):
    note = await find_note_or_404(note_id)
    require_note_access(note, current_user)

    update_data = {
        key: value
        for key, value in model_to_dict(updated_note).items()
        if value is not None
    }
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields provided for update")

    update_data["updatedAt"] = datetime.now(timezone.utc)
    result = await notes_collection.update_one(
        {"_id": ObjectId(note_id)}, {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")

    return serialize_note({**note, **update_data})


@router.delete("/{note_id}", summary="Delete note by ID")
async def delete_note(note_id: str, current_user=Depends(get_current_user)):
    note = await find_note_or_404(note_id)
    require_note_access(note, current_user)

    result = await notes_collection.delete_one({"_id": ObjectId(note_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")

    return {"message": "Note deleted successfully"}
