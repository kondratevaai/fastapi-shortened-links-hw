from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from domain.models import UserRole




class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="User name")
    email: str = Field(..., description="User email address")
    age: Optional[int] = Field(None, ge=0, le=150, description="User age")


class UserResponse(UserBase):
    """schema to return user data in api response"""
    id: int
    role: UserRole
    model_config = ConfigDict(from_attributes=True)


class UserRegistrationResponse(BaseModel):
    """schema for user registration response with token"""
    user: UserResponse
    access_token: str
    token_type: str = "bearer"


class ShortenLinkRequest(BaseModel):
    """schema to create a shortened link"""
    original_url: str = Field(..., description="original long url to shorten")
    custom_alias: Optional[str] = Field(None, min_length=3, max_length=100, description="custom alias for short link")
    expires_at: Optional[datetime] = Field(None, description="when link expires at")


class ShortenedLinkResponse(BaseModel):

    id: int
    short_code: str
    original_url: str
    custom_alias: Optional[str] = None
    user_id: Optional[int] = None
    click_count: int
    created_at: datetime
    last_accessed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class LinkStatsResponse(BaseModel):
    
    id: int
    short_code: str
    original_url: str
    custom_alias: Optional[str] = None
    click_count: int
    created_at: datetime
    last_accessed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_expired: bool
    days_since_creation: float
    model_config = ConfigDict(from_attributes=True)


class UpdateLinkRequest(BaseModel):
    original_url: Optional[str] = Field(None, description="new original url")
    expires_at: Optional[datetime] = Field(None, description="new expiration time")


class RequestsBase(BaseModel):
    text_raw: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="raw text input sent to ml model"
    )


class RequestResponse(RequestsBase):
    id: int
    user_id: int
    timestamp: datetime
    prediction: int
    processing_time_ms: Optional[float] = None
    text_length: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class StatsResponse(BaseModel):
    total_requests: int
    avg_processing_time_ms: float
    processing_time_quantiles: dict
    text_characteristics: dict
    prediction_distribution: dict