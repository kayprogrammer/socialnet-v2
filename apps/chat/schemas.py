from typing import List, Optional
from pydantic import Field, ValidationError, root_validator
from apps.common.schemas import (
    PaginatedResponseDataSchema,
    ResponseSchema,
    Schema,
    UserDataSchema,
)
from uuid import UUID
from datetime import datetime


class ChatSchema(Schema):
    id: UUID
    name: Optional[str]
    owner: UserDataSchema
    ctype: str
    description: Optional[str]
    image: Optional[str] = Field(..., alias="get_image")
    latest_message: Optional[dict]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_latest_message(obj):
        if len(obj.lmessages) > 0:
            message = obj.lmessages[0]
            return {
                "sender": UserDataSchema.from_orm(message.sender).dict(),
                "text": message.text,
                "file": message.get_file,
            }
        return None


class MessageSchema(Schema):
    id: UUID
    chat_id: UUID
    sender: UserDataSchema
    text: Optional[str]
    file: str = Field(..., alias="get_file")
    created_at: datetime
    updated_at: datetime


class MessageCreateSchema(Schema):
    chat_id: Optional[UUID]
    username: Optional[str]
    text: Optional[str]
    file_type: Optional[str] = Field(None, example="image/jpeg")

    @root_validator
    def validate_entry(cls, values):
        chat_id = values.get("chat_id")
        username = values.get("username")
        if not chat_id and not username:
            raise ValidationError(
                {"username": "You must enter the recipient's username"}
            )
        elif chat_id and username:
            raise ValidationError(
                {"username": "Can't enter username when chat_id is set"}
            )
        if not values.get("text") and not values.get("file_type"):
            raise ValidationError({"text": "You must enter a text"})
        return values


# RESPONSES
class ChatsResponseDataSchema(PaginatedResponseDataSchema):
    chats: List[ChatSchema] = Field(..., alias="items")


class ChatsResponseSchema(ResponseSchema):
    data: ChatsResponseDataSchema
