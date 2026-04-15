# /app/backend/models/user.py
# Modelos de Usuario

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    username: str
    name: str
    role: str = Field(default="usuario", pattern="^(superadmin|admin|usuario|optica)$")


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    is_active: bool
    last_login: Optional[str] = None
    created_at: str
    updated_at: str
    permissions: dict = {}


class UserListResponse(BaseModel):
    data: List[UserResponse]
    total: int


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
