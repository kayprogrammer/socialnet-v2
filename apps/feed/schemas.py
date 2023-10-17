from pydantic import BaseModel, Field
from apps.chat.models import CHAT_TYPES
from apps.common.schemas import (
    ResponseSchema,
    UserDataSchema,
    PaginatedResponseDataSchema,
)
from apps.common.file_processors import FileProcessor
from apps.common.validators import validate_file_type, validate_image_type
from apps.common.schema_examples import file_upload_data, user_data, latest_message_data
from django.utils.translation import gettext_lazy as _
from datetime import datetime
from typing import Optional, Dict, List


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


class PostsResponseDataSchema(PaginatedResponseDataSchema):
    posts: List[PostSchema] = Field(..., alias="items")


class PostsResponseSchema(ResponseSchema):
    data: PostsResponseDataSchema
