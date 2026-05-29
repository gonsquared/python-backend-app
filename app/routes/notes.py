from datetime import datetime, timezone
from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.database import db
from app.dependencies.auth import get_current_user
from app.helpers.user_helper import get_user_permissions
from app.models.note_model import Note, UpdateNote
from app.storage import LocalStorageBackend, get_storage
from app.utils import model_to_dict

router = APIRouter()
notes_collection = db["notes"]
users_collection = db["users"]
DEFAULT_LIMIT = 100
MAX_LIMIT = 100
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


def has_permission(user, permission: str) -> bool:
    return permission in get_user_permissions(user)


def can_manage_all_notes(user) -> bool:
    return has_permission(user, "manage_notes")


def can_manage_own_notes(user) -> bool:
    return has_permission(user, "manage_own_notes")


def note_belongs_to_user(note, user) -> bool:
    return note.get("user") == str(user.get("_id"))


def require_note_access(note, current_user):
    if can_manage_all_notes(current_user):
        return

    if can_manage_own_notes(current_user) and note_belongs_to_user(
        note, current_user
    ):
        return

    raise HTTPException(status_code=403, detail="You can only manage your own notes")


def require_manage_own_notes(current_user):
    if can_manage_own_notes(current_user):
        return

    raise HTTPException(status_code=403, detail="Manage own notes permission is required")


def serialize_note(note, user_name: str = None):
    return {
        "id": str(note["_id"]),
        "title": note["title"],
        "contents": note.get("contents", ""),
        "user": note["user"],
        "userName": user_name or note["user"],
        "createdAt": note.get("createdAt"),
        "updatedAt": note.get("updatedAt"),
        "color": note.get("color"),
        "isPinned": note.get("isPinned", False),
        "labels": note.get("labels", []),
        "noteType": note.get("noteType", "text"),
        "checklistItems": note.get("checklistItems", []),
        "reminderAt": note.get("reminderAt"),
        "imagePath": note.get("imagePath"),
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
    require_manage_own_notes(current_user)

    now = datetime.now(timezone.utc)
    note_dict = model_to_dict(note)
    note_dict["user"] = str(current_user["_id"])
    note_dict["createdAt"] = now
    note_dict["updatedAt"] = now

    result = await notes_collection.insert_one(note_dict.copy())
    return serialize_note({"_id": result.inserted_id, **note_dict})


@router.get("/", summary="Get notes")
async def get_notes(
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    skip: Annotated[int, Query(ge=0)] = 0,
    current_user=Depends(get_current_user),
):
    if can_manage_all_notes(current_user):
        query = {}
    elif can_manage_own_notes(current_user):
        query = {"user": str(current_user["_id"])}
    else:
        raise HTTPException(
            status_code=403, detail="Manage own notes permission is required"
        )

    notes = await notes_collection.find(query).skip(skip).limit(limit).to_list(limit)

    user_ids = list({ObjectId(note["user"]) for note in notes if ObjectId.is_valid(note.get("user", ""))})
    users = await users_collection.find({"_id": {"$in": user_ids}}, {"_id": 1, "firstName": 1, "lastName": 1}).to_list(len(user_ids))
    user_name_map = {str(u["_id"]): f"{u.get('firstName', '')} {u.get('lastName', '')}".strip() for u in users}

    return [serialize_note(note, user_name_map.get(note["user"], note["user"])) for note in notes]


@router.get("/by-user/{user_id}", summary="Get notes by user")
async def get_notes_by_user(
    user_id: str,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    skip: Annotated[int, Query(ge=0)] = 0,
    current_user=Depends(get_current_user),
):
    validate_user_id(user_id)
    if can_manage_all_notes(current_user):
        notes = (
            await notes_collection.find({"user": user_id})
            .skip(skip)
            .limit(limit)
            .to_list(limit)
        )
        return [serialize_note(note) for note in notes]

    if not can_manage_own_notes(current_user):
        raise HTTPException(
            status_code=403, detail="Manage own notes permission is required"
        )

    if str(current_user.get("_id")) != user_id:
        raise HTTPException(status_code=403, detail="You can only manage your own notes")

    notes = (
        await notes_collection.find({"user": user_id})
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )
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
        if key in updated_note.model_fields_set
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

    if note.get("imagePath"):
        get_storage().delete(note["imagePath"])

    return {"message": "Note deleted successfully"}


@router.post("/{note_id}/image", summary="Upload image for a note")
async def upload_note_image(
    note_id: str,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    storage: LocalStorageBackend = Depends(get_storage),
):
    note = await find_note_or_404(note_id)
    require_note_access(note, current_user)

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, GIF, and WebP images are allowed")

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image must be under 5MB")

    if note.get("imagePath"):
        storage.delete(note["imagePath"])

    filename = await storage.save(file.filename or "upload", content)

    await notes_collection.update_one(
        {"_id": ObjectId(note_id)},
        {"$set": {"imagePath": filename}},
    )
    return {"imagePath": filename}
