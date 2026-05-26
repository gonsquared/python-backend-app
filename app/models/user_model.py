from typing import Literal

from pydantic import BaseModel, EmailStr, Field
from typing import Optional

UserStatus = Literal["inactive", "active", "archived"]
UserRole = Literal["admin", "user"]

# create user schema
class User(BaseModel):
    firstName: str = Field(..., min_length=2, max_length=100, description="First name must be between 2 and 100 characters")
    lastName: str = Field(..., min_length=2, max_length=100, description="Last name must be between 2 and 100 characters")
    email: EmailStr = Field(..., description="Valid email address is required")
    password: Optional[str] = Field(None, min_length=12, max_length=128, description="Password must be between 12 and 128 characters")
    status: UserStatus = Field("inactive", description="User lifecycle status")
    role: UserRole = Field("user", description="User access role")

# update user schema PUT and PATCH
class UpdateUser(BaseModel):
    firstName: Optional[str] = Field(None, min_length=2, max_length=100, description="First name must be between 2 and 100 characters")
    lastName: Optional[str] = Field(None, min_length=2, max_length=100, description="Last name must be between 2 and 100 characters")
    email: Optional[EmailStr] = Field(None, description="Valid email address if updating email")
    password: Optional[str] = Field(None, min_length=12, max_length=128, description="Password must be between 12 and 128 characters")
    status: Optional[UserStatus] = Field(None, description="User lifecycle status")
    role: Optional[UserRole] = Field(None, description="User access role")


class RegisterUser(BaseModel):
    firstName: str = Field(..., min_length=2, max_length=100, description="First name must be between 2 and 100 characters")
    lastName: str = Field(..., min_length=2, max_length=100, description="Last name must be between 2 and 100 characters")
    email: EmailStr = Field(..., description="Valid email address is required")
    password: str = Field(..., min_length=12, max_length=128, description="Password must be between 12 and 128 characters")
    verifyPassword: str = Field(..., min_length=12, max_length=128, description="Password confirmation must be between 12 and 128 characters")


class LoginUser(BaseModel):
    email: EmailStr = Field(..., description="Valid email address is required")
    password: str = Field(..., min_length=1, max_length=128, description="Password is required")
