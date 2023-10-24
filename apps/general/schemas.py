from apps.common.schemas import Schema, ResponseSchema


# Site Details
class SiteDetailDataSchema(Schema):
    name: str
    email: str
    phone: str
    address: str
    fb: str
    tw: str
    wh: str
    ig: str


class SiteDetailResponseSchema(ResponseSchema):
    data: SiteDetailDataSchema
