from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# create user schema
class User(BaseModel):
    firstName: str = Field(..., min_length=2, max_length=100, description="First name must be between 2 and 100 characters")
    lastName: str = Field(..., min_length=2, max_length=100, description="Last name must be between 2 and 100 characters")
    email: EmailStr = Field(..., description="Valid email address is required")

# update user schema PUT and PATCH
class UpdateUser(BaseModel):
    firstName: Optional[str] = Field(None, min_length=2, max_length=100, description="First name must be between 2 and 100 characters")
    lastName: Optional[str] = Field(None, min_length=2, max_length=100, description="Last name must be between 2 and 100 characters")
    email: Optional[EmailStr] = Field(None, description="Valid email address if updating email")
