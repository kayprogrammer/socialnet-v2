from uuid import UUID
from pydantic import Field, validator
from apps.chat.models import CHAT_TYPES
from apps.common.models import File
from apps.common.schemas import (
    BaseModel,
    ResponseSchema,
    UserDataSchema,
    PaginatedResponseDataSchema,
)
from apps.common.file_processors import FileProcessor
from apps.common.validators import validate_file_type, validate_image_type
from apps.common.schema_examples import file_upload_data, user_data, latest_message_data
from django.utils.translation import gettext_lazy as _
from datetime import datetime
from typing import Any, Optional, Dict, List


class PostSchema(BaseModel):
    author: UserDataSchema
    text: str
    slug: str = Field(..., example="john-doe-d10dde64-a242-4ed0-bd75-4c759644b3a6")
    reactions_count: int
    comments_count: int
    image: Optional[str] = Field(..., example="https://img.url", alias="get_image")
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class PostInputSchema(BaseModel):
    text: str
    file_type: Optional[str] = Field(None, example="image/jpeg")

    @validator("file_type")
    def validate_img_type(cls, v):
        return validate_image_type(v)


class PostsResponseDataSchema(PaginatedResponseDataSchema):
    posts: List[PostSchema] = Field(..., alias="items")


class PostsResponseSchema(ResponseSchema):
    data: PostsResponseDataSchema


class PostInputResponseDataSchema(PostSchema):
    image: Optional[Any] = Field(..., exclude=True, hidden=True)
    image_id: Optional[UUID] = Field(..., exclude=True, hidden=True)
    image_upload_status: bool = Field(..., exclude=True, hidden=True)
    file_upload_data: Optional[Dict] = Field(None, example=file_upload_data)
    reactions_count: int = Field(None, exclude=True, hidden=True)
    comments_count: int = Field(None, exclude=True, hidden=True)

    @validator("file_upload_data", always=True)
    def show_file_upload_data(cls, v, values):
        if values["image_upload_status"]:
            return FileProcessor.generate_file_signature(
                key=values["image_id"],
                folder="posts",
            )
        return v


class PostInputResponseSchema(ResponseSchema):
    data: PostInputResponseDataSchema
