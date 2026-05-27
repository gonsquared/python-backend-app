from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

NoteStatus = Literal["published", "not published", "archived"]
NoteType = Literal["text", "checklist"]
NoteColor = Literal[
    "red", "pink", "orange", "yellow", "teal",
    "green", "cyan", "blue", "purple", "gray"
]


class ChecklistItem(BaseModel):
    text: str
    checked: bool = False


class Note(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    contents: str = Field(default="")
    status: NoteStatus = Field("not published")
    color: Optional[NoteColor] = None
    isPinned: bool = False
    labels: List[str] = Field(default_factory=list)
    noteType: NoteType = "text"
    checklistItems: List[ChecklistItem] = Field(default_factory=list)
    reminderAt: Optional[datetime] = None


class UpdateNote(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    contents: Optional[str] = None
    status: Optional[NoteStatus] = None
    color: Optional[NoteColor] = None
    isPinned: Optional[bool] = None
    labels: Optional[List[str]] = None
    noteType: Optional[NoteType] = None
    checklistItems: Optional[List[ChecklistItem]] = None
    reminderAt: Optional[datetime] = None
