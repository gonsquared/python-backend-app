from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# create user schema
class User(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Name must be between 2 and 100 characters")
    email: EmailStr = Field(..., description="Valid email address is required")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age must be between 0 and 120 if provided")

# update user schema PUT and PATCH
class UpdateUser(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Name must be between 2 and 100 characters")
    email: Optional[EmailStr] = Field(None, description="Valid email address if updating email")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age must be between 0 and 120 if provided")
