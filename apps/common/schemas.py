from pydantic import BaseModel


class ResponseSchema(BaseModel):
    status: str = "success"
    message: str
