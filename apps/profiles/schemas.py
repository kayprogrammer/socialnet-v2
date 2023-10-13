from typing import List, Optional, Any, Union

from pydantic import UUID4, BaseModel, EmailStr, validator, Field, StrictStr
from datetime import datetime
from uuid import UUID
from apps.common.schemas import ResponseSchema

from apps.common.file_types import ALLOWED_IMAGE_TYPES
from apps.common.file_processors import FileProcessor
from pytz import UTC
from decimal import Decimal


class CitySchema(BaseModel):
    id: int
    name: str
    region: str
    country: str

    class Config:
        orm_mode = True


class CitiesResponseSchema(ResponseSchema):
    data: List[CitySchema]


class ProfileSchema(BaseModel):
    first_name: str = Field(..., example="John", max_length=50)
    last_name: str = Field(..., example="Doe", max_length=50)
    username: str = Field(..., example="john-doe", readonly=True)
    email: EmailStr = Field(..., example="johndoe@email.com", readonly=True)
    avatar: Optional[str] = Field(..., example="https://img.com", readonly=True)
    bio: Optional[str] = Field(
        ..., example="Software Engineer | Django Ninja Developer", max_length=200
    )
    dob: Optional[datetime]
    city: Optional[str] = Field(..., example="Lagos", readonly=True)
    city_id: Optional[UUID4] = Field(..., writeonly=True)
    created_at: datetime = Field(..., readonly=True)
    updated_at: datetime = Field(..., readonly=True)
    file_type: Optional[str] = Field(..., example="image/jpeg", writeonly=True)

    class Config:
        orm_mode = True


class ProfilesResponseSchema(ResponseSchema):
    data: List[ProfileSchema] = []


#     @validator("file_type")
#     def validate_file_type(cls, v):
#         if not v in ALLOWED_IMAGE_TYPES:
#             raise ValueError("Image type not allowed!")
#         return v

#     @validator("price")
#     def validate_price(cls, v):
#         if v <= 0:
#             raise ValueError("Must be greater than 0!")
#         return v


# class UpdateListingSchema(BaseModel):
#     name: Optional[StrictStr] = Field(None, example="Product name")
#     desc: Optional[str] = Field(None, example="Product description")
#     category: Optional[StrictStr] = Field(None, example="category_slug")
#     price: Optional[Decimal] = Field(None, example=1000.00, decimal_places=2)
#     closing_date: Optional[datetime]
#     active: Optional[bool]
#     file_type: Optional[str] = Field(None, example="image/jpeg")

#     @validator("name")
#     def validate_name(cls, v):
#         if len(v) > 70:
#             raise ValueError("70 characters max")
#         return v

#     @validator("closing_date")
#     def validate_closing_date(cls, v):
#         if datetime.utcnow().replace(tzinfo=UTC) > v:
#             raise ValueError("Closing date must be beyond the current datetime!")
#         return v

#     @validator("file_type")
#     def validate_file_type(cls, v):
#         if not v in ALLOWED_IMAGE_TYPES:
#             raise ValueError("Image type not allowed!")
#         return v

#     @validator("price")
#     def validate_price(cls, v):
#         if v <= 0:
#             raise ValueError("Must be greater than 0!")
#         return v

#     class Config:
#         error_msg_templates = {
#             "value_error.any_str.max_length": "70 characters max!",
#         }


# class CreateListingResponseDataSchema(BaseModel):
#     name: str
#     auctioneer: dict = Field(
#         ..., example={"name": "John Doe", "avatar": "https://image.url"}
#     )

#     slug: str
#     desc: str

#     category: Optional[str]

#     price: Decimal = Field(..., example=1000.00, decimal_places=2)
#     closing_date: Any
#     active: bool
#     bids_count: int
#     image_id: UUID = Field(..., example="Ignore this")
#     file_upload_data: Optional[dict]

#     @validator("file_upload_data", always=True)
#     def assemble_file_upload_data(cls, v, values):
#         image_id = values.get("image_id")
#         if image_id:
#             values.pop("image_id", None)
#             return FileProcessor.generate_file_signature(
#                 key=image_id,
#                 folder="listings",
#             )
#         values.pop("image_id", None)
#         return None

#     @validator("auctioneer", pre=True)
#     def show_auctioneer(cls, v):
#         avatar = None
#         if v.avatar_id:
#             avatar = FileProcessor.generate_file_url(
#                 key=v.avatar_id,
#                 folder="avatars",
#                 content_type=v.avatar.resource_type,
#             )
#         return {"name": v.full_name, "avatar": avatar}

#     @validator("category", pre=True)
#     def show_category(cls, v):
#         return v.name if v else "Other"

#     class Config:
#         orm_mode = True


# class CreateListingResponseSchema(ResponseSchema):
#     data: CreateListingResponseDataSchema


# # ---------------------------------------------------------- #

# # USER PROFILE #


# class UpdateProfileSchema(BaseModel):
#     first_name: str = Field(..., example="John")
#     last_name: str = Field(..., example="Doe")
#     file_type: Optional[str] = Field(None, example="image/png")

#     @validator("first_name", "last_name")
#     def validate_name(cls, v):
#         if len(v.split(" ")) > 1:
#             raise ValueError("No spacing allowed")
#         elif len(v) > 50:
#             raise ValueError("50 characters max")
#         return v

#     @validator("file_type")
#     def validate_file_type(cls, v):
#         if v and v not in ALLOWED_IMAGE_TYPES:
#             raise ValueError("Image type not allowed!")
#         return v


# # RESPONSE FOR PUT REQUEST
# class UpdateProfileResponseDataSchema(BaseModel):
#     first_name: str
#     last_name: str
#     avatar_id: Optional[UUID] = Field(..., example="Ignore this")
#     file_upload_data: Optional[dict]

#     @validator("file_upload_data", always=True)
#     def assemble_file_upload_data(cls, v, values):
#         avatar_id = values.get("avatar_id")
#         if avatar_id:
#             values.pop("avatar_id", None)
#             return FileProcessor.generate_file_signature(
#                 key=avatar_id,
#                 folder="avatars",
#             )
#         values.pop("avatar_id", None)
#         return None

#     class Config:
#         orm_mode = True


# class UpdateProfileResponseSchema(ResponseSchema):
#     data: UpdateProfileResponseDataSchema


# # RESPONSE FOR GET REQUEST
# class ProfileDataSchema(BaseModel):
#     first_name: str
#     last_name: str
#     avatar: Optional[Union[dict, str]]

#     @validator("avatar", pre=True)
#     def assemble_image_url(cls, v):
#         if v:
#             return FileProcessor.generate_file_url(
#                 key=v.id, folder="avatars", content_type=v.resource_type
#             )
#         return None

#     class Config:
#         orm_mode = True


# class ProfileResponseSchema(ResponseSchema):
#     data: ProfileDataSchema


# # ---------------------------------------- #
