from pydantic import BaseModel
from apps.common.schemas import ResponseSchema


# Site Details
class SiteDetailDataSchema(BaseModel):
    name: str
    email: str
    phone: str
    address: str
    fb: str
    tw: str
    wh: str
    ig: str

    class Config:
        orm_mode = True


class SiteDetailResponseSchema(ResponseSchema):
    data: SiteDetailDataSchema
