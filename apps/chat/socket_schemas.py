from typing import Literal
from pydantic import BaseModel, UUID4


class SocketMessageSchema(BaseModel):
    status: Literal["CREATED", "UPDATED", "DELETED"]
    id: UUID4
