from pydantic import BaseModel as _BaseModel


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
