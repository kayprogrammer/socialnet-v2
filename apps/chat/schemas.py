from typing import Any, Dict, List, Optional
from pydantic import Field, ValidationError, root_validator, validator
from apps.common.file_processors import FileProcessor
from apps.common.schemas import (
    PaginatedResponseDataSchema,
    ResponseSchema,
    Schema,
    UserDataSchema,
)
from uuid import UUID
from datetime import datetime
from apps.common.schema_examples import file_upload_data

from apps.common.validators import validate_file_type, validate_image_type


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
    file: Optional[str] = Field(..., alias="get_file")
    created_at: datetime
    updated_at: datetime


class MessageUpdateSchema(Schema):
    file_type: Optional[str] = Field(None, example="image/jpeg")
    text: Optional[str]

    @validator("text", always=True)
    def validate_text(cls, v, values):
        if not v and not values.get("file_type"):
            raise ValueError("You must enter a text")
        return v

    @validator("file_type", always=True)
    def validate_file_type(cls, v):
        return validate_file_type(v)


class MessageCreateSchema(MessageUpdateSchema):
    chat_id: Optional[UUID]
    username: Optional[str]

    @validator("username", always=True)
    def validate_username(cls, v, values):
        chat_id = values.get("chat_id")
        if not chat_id and not v:
            raise ValueError("You must enter the recipient's username")
        elif chat_id and v:
            raise ValueError("Can't enter username when chat_id is set")
        return v


class MessagesResponseDataSchema(PaginatedResponseDataSchema):
    items: List[MessageSchema]


class MessagesSchema(Schema):
    chat: ChatSchema
    messages: MessagesResponseDataSchema
    users: List[UserDataSchema]


class GroupChatSchema(Schema):
    id: UUID
    name: str
    description: Optional[str]
    image: Optional[str] = Field(..., alias="get_image")
    users: List[UserDataSchema] = Field(..., alias="recipients")


class GroupChatInputSchema(Schema):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(..., max_length=1000)
    usernames_to_add: List[str]
    usernames_to_remove: List[str]
    file_type: Optional[str] = Field(..., example="image/jpeg")

    @validator("file_type", always=True)
    def validate_img_type(cls, v):
        return validate_image_type(v)


class GroupChatCreateSchema(GroupChatInputSchema):
    usernames_to_remove: List[str] = Field(None, exclude=True, hidden=True)


# RESPONSES
class ChatsResponseDataSchema(PaginatedResponseDataSchema):
    chats: List[ChatSchema] = Field(..., alias="items")


class ChatsResponseSchema(ResponseSchema):
    data: ChatsResponseDataSchema


class ChatResponseSchema(ResponseSchema):
    data: MessagesSchema


class MessageCreateResponseDataSchema(MessageSchema):
    file: Optional[Any] = Field(..., exclude=True, hidden=True)
    file_upload_data: Optional[Dict] = Field(None, example=file_upload_data)

    @staticmethod
    def resolve_file_upload_data(obj):
        if obj.file_upload_status:
            return FileProcessor.generate_file_signature(
                key=obj.file_id,
                folder="messages",
            )
        return None


class MessageCreateResponseSchema(ResponseSchema):
    data: MessageCreateResponseDataSchema


class GroupChatInputResponseDataSchema(GroupChatSchema):
    image: Optional[Any] = Field(..., exclude=True, hidden=True)
    file_upload_data: Optional[Dict] = Field(None, example=file_upload_data)

    @staticmethod
    def resolve_file_upload_data(obj):
        if obj.file_upload_status:
            return FileProcessor.generate_file_signature(
                key=obj.image_id,
                folder="groups",
            )
        return None


class GroupChatInputResponseSchema(ResponseSchema):
    data: GroupChatInputResponseDataSchema
