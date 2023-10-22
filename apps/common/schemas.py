from pydantic import Field, BaseModel as _BaseModel
from typing import Optional


class BaseModel(_BaseModel):
    class Config:
        @staticmethod
        def schema_extra(schema: dict, _):
            props = {}
            for k, v in schema.get("properties", {}).items():
                if not v.get("hidden", False):
                    props[k] = v
            schema["properties"] = props


class ResponseSchema(BaseModel):
    status: str = "success"
    message: str


class ErrorResponseSchema(ResponseSchema):
    status: str = "failure"


class PaginatedResponseDataSchema(BaseModel):
    per_page: int
    current_page: int
    last_page: int


class UserDataSchema(BaseModel):
    name: str = Field(..., alias="full_name")
    username: str
    avatar: str = Field(None, alias="get_avatar")

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "name": "John Doe",
                "username": "john-doe",
                "avatar": "https://img.url",
            }
        }
