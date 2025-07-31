from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

class TaskBase(BaseModel):
    user: EmailStr
    label: str
    status: str = Field(..., regex="^(pending|on-going|done)$")

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    label: Optional[str] = None
    status: Optional[str] = Field(None, regex="^(pending|on-going|done)$")

class TaskResponse(TaskBase):
    id: str = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime
