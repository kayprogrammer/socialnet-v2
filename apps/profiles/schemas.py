from typing import Dict, List, Optional, Any, Union
from pydantic import UUID4, BaseModel, EmailStr, validator, Field
from datetime import datetime, date
from apps.common.schemas import PaginatedResponseDataSchema, ResponseSchema

from apps.common.file_types import ALLOWED_IMAGE_TYPES
from apps.common.file_processors import FileProcessor
from pytz import UTC


class CitySchema(BaseModel):
    id: int
    name: str
    region: str = Field(..., alias="region_name")
    country: str = Field(..., alias="country_name")

    class Config:
        orm_mode = True


class CitiesResponseSchema(ResponseSchema):
    data: List[CitySchema]


class ProfileSchema(BaseModel):
    first_name: str = Field(..., example="John")
    last_name: str = Field(..., example="Doe")
    username: str = Field(..., example="john-doe")
    email: EmailStr = Field(..., example="johndoe@email.com")
    avatar: Optional[str] = Field(..., example="https://img.com", alias="get_avatar")
    bio: Optional[str] = Field(
        ..., example="Software Engineer | Django Ninja Developer"
    )
    dob: Optional[date]
    city: Optional[str] = Field(None, example="Lagos", alias="city_name")
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ProfileUpdateSchema(BaseModel):
    first_name: Optional[str] = Field(None, example="John", max_length=50, min_length=1)
    last_name: Optional[str] = Field(None, example="Doe", max_length=50, min_length=1)
    bio: Optional[str] = Field(
        None,
        example="Software Engineer | Django Ninja Developer",
        max_length=200,
        min_length=1,
    )
    dob: Optional[date]
    city_id: Optional[int]
    file_type: Optional[str] = Field(None, example="image/jpeg")

    @validator("file_type")
    def validate_file_type(cls, v):
        if v and v not in ALLOWED_IMAGE_TYPES:
            raise ValueError("Image type not allowed!")
        return v


class DeleteUserSchema(BaseModel):
    password: str


class ProfilesResponseDataSchema(PaginatedResponseDataSchema):
    users: List[ProfileSchema] = Field(..., alias="items")


class ProfilesResponseSchema(ResponseSchema):
    data: ProfilesResponseDataSchema


class ProfileResponseSchema(ResponseSchema):
    data: ProfileSchema


class ProfileUpdateResponseDataSchema(ProfileSchema):
    avatar_id: UUID4
    image_upload_status: bool
    file_upload_data: Optional[Dict]

    @validator("file_upload_data", always=True)
    def show_file_upload_data(cls, v, values):
        values.pop("avatar", None)
        image_upload_status = values.pop("image_upload_status")
        avatar_id = values.pop("avatar_id", None)
        if image_upload_status:
            return FileProcessor.generate_file_signature(
                key=avatar_id,
                folder="avatars",
            )
        return v


class ProfileUpdateResponseSchema(ResponseSchema):
    data: ProfileUpdateResponseDataSchema
