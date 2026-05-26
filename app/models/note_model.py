from typing import Literal, Optional

from pydantic import BaseModel, Field

NoteStatus = Literal["published", "not published", "archived"]


class Note(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    contents: str = Field(..., min_length=1)
    status: NoteStatus = Field("not published")


class UpdateNote(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    contents: Optional[str] = Field(None, min_length=1)
    status: Optional[NoteStatus] = None
