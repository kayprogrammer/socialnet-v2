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


class PaginatedResponseDataSchema(BaseModel):
    per_page: int
    current_page: int
    last_page: int


class UserDataSchema(BaseModel):
    full_name: str = Field(..., example="John Doe")
    username: str = Field(..., example="john-doe")
    avatar: Optional[str] = Field(None, example="https://img.url", alias="get_avatar")

    class Config:
        orm_mode = True
