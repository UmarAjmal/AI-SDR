from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from packages.common.models.user import UserStatus

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    workspace_name: str = Field(..., min_length=2, max_length=100)

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    active_workspace_id: str
    active_role: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    status: UserStatus
    created_at: datetime
