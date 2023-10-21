from enum import Enum
from uuid import UUID
from pydantic import Field, validator
from apps.common.schemas import (
    BaseModel,
    ResponseSchema,
    UserDataSchema,
    PaginatedResponseDataSchema,
)
from apps.common.file_processors import FileProcessor
from apps.common.validators import validate_image_type
from apps.common.schema_examples import file_upload_data
from datetime import datetime
from typing import Any, Optional, Dict, List

from apps.feed.models import REACTION_CHOICES


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


class PostResponseSchema(ResponseSchema):
    data: PostSchema


# REACTIONS
class ReactionSchema(BaseModel):
    id: UUID
    user: UserDataSchema
    rtype: str = "LIKE"

    class Config:
        orm_mode = True


class ReactionInputSchema(BaseModel):
    rtype: Enum("ReactionType", REACTION_CHOICES)


class ReactionsResponseDataSchema(PaginatedResponseDataSchema):
    reactions: List[ReactionSchema] = Field(..., alias="items")


class ReactionsResponseSchema(ResponseSchema):
    data: ReactionsResponseDataSchema


class ReactionResponseSchema(ResponseSchema):
    data: ReactionSchema


# COMMENTS AND REPLIES


class ReplySchema(BaseModel):
    author: UserDataSchema
    slug: str
    text: str

    class Config:
        orm_mode = True


class CommentSchema(ReplySchema):
    replies_count: int

    class Config:
        orm_mode = True


class CommentWithRepliesResponseDataSchema(PaginatedResponseDataSchema):
    items: List[ReplySchema]


class CommentWithRepliesSchema(BaseModel):
    comment: CommentSchema
    replies: CommentWithRepliesResponseDataSchema


class CommentInputSchema(BaseModel):
    text: str


class CommentsResponseDataSchema(PaginatedResponseDataSchema):
    comments: List[CommentSchema] = Field(..., alias="items")


class CommentsResponseSchema(ResponseSchema):
    data: CommentsResponseDataSchema


class CommentResponseSchema(ResponseSchema):
    data: CommentSchema


class CommentWithRepliesResponseSchema(ResponseSchema):
    data: CommentWithRepliesSchema


class ReplyResponseSchema(ResponseSchema):
    data: ReplySchema
