from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginIn(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool = True

class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
