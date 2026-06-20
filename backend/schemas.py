from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List, Optional

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class AccountCreate(BaseModel):
    provider: str
    display_name: str
    credentials: Optional[Dict] = None
    quota_limit: Optional[int] = 5 * 1024 * 1024 * 1024  # default 5 GB
    is_mock: Optional[bool] = False

class AccountResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    provider: str
    display_name: str
    quota_limit: int
    used_space: int
    is_active: bool
    is_mock: bool

    class Config:
        from_attributes = True

class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None

class FolderResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    name: str
    parent_id: Optional[str] = None

    class Config:
        from_attributes = True

class FileResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    folder_id: Optional[str] = None
    original_name: str
    stored_name: str
    compression_type: str
    original_size: int
    compressed_size: int
    cloud_provider: str
    web_link: Optional[str] = None
    account_id: str
    upload_time: datetime

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    action: str
    details: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_files: int
    original_size_total: int
    compressed_size_total: int
    space_saved_bytes: int
    saving_ratio: float
    provider_distribution: Dict[str, int]
    account_usage: List[Dict]
