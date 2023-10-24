from ninja import Field, Schema as _Schema
from apps.common.schema_examples import user_data


class Schema(_Schema):
    class Config:
        arbitrary_types_allowed = True

        @staticmethod
        def schema_extra(schema: dict, _):
            props = {}
            for k, v in schema.get("properties", {}).items():
                if not v.get("hidden", False):
                    props[k] = v
            schema["properties"] = props


class ResponseSchema(Schema):
    status: str = "success"
    message: str


class ErrorResponseSchema(ResponseSchema):
    status: str = "failure"


class PaginatedResponseDataSchema(Schema):
    per_page: int
    current_page: int
    last_page: int


class UserDataSchema(Schema):
    name: str = Field(..., alias="full_name")
    username: str
    avatar: str = Field(None, alias="get_avatar")

    class Config:
        schema_extra = {"example": user_data}
