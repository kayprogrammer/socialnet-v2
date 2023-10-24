from typing import Any, Dict, List, Optional
from pydantic import EmailStr, validator, Field
from datetime import datetime, date
from apps.common.schemas import (
    Schema,
    PaginatedResponseDataSchema,
    ResponseSchema,
    UserDataSchema,
)
from apps.common.schema_examples import file_upload_data
from apps.common.file_processors import FileProcessor
from uuid import UUID

from apps.common.validators import validate_image_type


class CitySchema(Schema):
    id: int
    name: str
    region: str = Field(..., alias="region_name")
    country: str = Field(..., alias="country_name")


class CitiesResponseSchema(ResponseSchema):
    data: List[CitySchema]


class ProfileSchema(Schema):
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


class ProfileUpdateSchema(Schema):
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
    def validate_img_type(cls, v):
        return validate_image_type(v)


class DeleteUserSchema(Schema):
    password: str


class ProfilesResponseDataSchema(PaginatedResponseDataSchema):
    users: List[ProfileSchema] = Field(..., alias="items")


class ProfilesResponseSchema(ResponseSchema):
    data: ProfilesResponseDataSchema


class ProfileResponseSchema(ResponseSchema):
    data: ProfileSchema


class ProfileUpdateResponseDataSchema(ProfileSchema):
    avatar: Optional[Any] = Field(..., exclude=True, hidden=True)
    file_upload_data: Optional[Dict] = Field(None, example=file_upload_data)

    @staticmethod
    def resolve_file_upload_data(obj):
        if obj.image_upload_status:
            return FileProcessor.generate_file_signature(
                key=obj.avatar_id,
                folder="avatars",
            )
        return None


class ProfileUpdateResponseSchema(ResponseSchema):
    data: ProfileUpdateResponseDataSchema


class SendFriendRequestSchema(Schema):
    username: str


class AcceptFriendRequestSchema(SendFriendRequestSchema):
    accepted: bool


class NotificationSchema(Schema):
    id: UUID
    sender: Optional[UserDataSchema]
    ntype: str = Field(..., example="REACTION")
    message: str = Field(..., example="John Doe reacted to your post")
    post_slug: Optional[str]
    comment_slug: Optional[str]
    reply_slug: Optional[str]
    is_read: bool = False


class ReadNotificationSchema(Schema):
    mark_all_as_read: bool
    id: Optional[UUID]

    @validator("id", always=True)
    def validate_id(cls, v, values):
        if not v and not values["mark_all_as_read"]:
            raise ValueError("Set ID or mark all as read as True")
        return v


class NotificationsResponseDataSchema(PaginatedResponseDataSchema):
    notifications: List[NotificationSchema] = Field(..., alias="items")


class NotificationsResponseSchema(ResponseSchema):
    data: NotificationsResponseDataSchema
