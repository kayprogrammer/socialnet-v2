from pydantic import BaseModel


class ResponseSchema(BaseModel):
    status: str = "success"
    message: str


class PaginatedResponseDataSchema(BaseModel):
    per_page: int
    current_page: int
    last_page: int
