from typing import Optional
from django.db.models import Q, Case, When, Value, BooleanField, F
from ninja.router import Router
from apps.accounts.models import User
from apps.common.error import ErrorCode
from apps.common.exceptions import RequestError
from apps.common.models import File
from apps.common.paginators import CustomPagination
from apps.common.responses import CustomResponse
from apps.common.schemas import ResponseSchema
from apps.common.utils import AuthUser, set_dict_attr
from apps.common.file_types import ALLOWED_IMAGE_TYPES
from asgiref.sync import sync_to_async

from apps.profiles.schemas import (
    CitiesResponseSchema,
    DeleteUserSchema,
    ProfileResponseSchema,
    ProfileUpdateResponseSchema,
    ProfileUpdateSchema,
    ProfilesResponseSchema,
)
from cities_light.models import City
import re

profiles_router = Router(tags=["Profiles"])

paginator = CustomPagination()


def get_users_queryset(current_user):
    users = User.objects.annotate(city_name=F("city__name")).select_related("avatar")
    if current_user:
        users = users.exclude(id=current_user.id)
        if current_user.city:
            # Order by the current user region or country
            city = current_user.city
            region = city.region.name if city.region else None
            country = city.country.name
            order_by_val = (
                Q(city__region__name=region)
                if region
                else Q(city__country__name=country)
            )

            users = users.annotate(
                ordering_field=Case(
                    When(order_by_val, then=Value(True)),
                    default=Value(
                        False
                    ),  # Use False as a default value if the condition doesn't match
                    output_field=BooleanField(),
                )
            ).annotate(
                has_city=Case(
                    When(city__isnull=False, then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                )
            )
            # Order the users by the 'ordering_field' and "has_city" field in descending order
            users = users.order_by("-has_city", "-ordering_field")
    return users


@profiles_router.get(
    "",
    summary="Retrieve Users",
    description="This endpoint retrieves a paginated list of users",
    response=ProfilesResponseSchema,
    auth=AuthUser(),
)
async def retrieve_users(request, page: int = 1):
    paginator.page_size = 15
    user = request.auth
    user = await user if user else None
    users = get_users_queryset(user)
    paginated_data = await paginator.paginate_queryset(users, page)
    return CustomResponse.success(message="Users fetched", data=paginated_data)


@profiles_router.get(
    "/cities/",
    summary="Retrieve cities based on query params",
    description="This endpoint retrieves a first 10 cities that matches the query params",
    response=CitiesResponseSchema,
)
async def retrieve_cities(request, name: str = None):
    cities = []
    message = "Cities Fetched"
    if name:
        name = re.sub(r"[^\w\s]", "", name)  # Remove special chars
        cities = await sync_to_async(list)(
            City.objects.filter(name__startswith=name).annotate(
                region_name=F("region__name"), country_name=F("country__name")
            )[:10]
        )
    if len(cities) == 0:
        message = "No match found"
    return CustomResponse.success(message=message, data=cities)


@profiles_router.get(
    "/profile/{username}/",
    summary="Retrieve user's profile",
    description="This endpoint retrieves a particular user profile",
    response=ProfileResponseSchema,
)
async def retrieve_user_profile(request, username: str):
    user = (
        await User.objects.annotate(city_name=F("city__name"))
        .select_related("avatar")
        .aget_or_none(username=username)
    )
    if not user:
        raise RequestError(
            err_code=ErrorCode.NON_EXISTENT,
            err_msg="No user with that username",
            status_code=404,
        )
    return CustomResponse.success(message="User details fetched", data=user)


@profiles_router.patch(
    "/profile/",
    summary="Update user's profile",
    description=f"""
        This endpoint updates a particular user profile
        ALLOWED FILE TYPES: {", ".join(ALLOWED_IMAGE_TYPES)}
    """,
    response=ProfileUpdateResponseSchema,
    auth=AuthUser(),
)
async def update_profile(request, data: ProfileUpdateSchema):
    user = await request.auth
    data = data.dict(exclude_none=True)
    # Validate City ID Entry
    user.city_name = user.city.name
    city_id = data.pop("city_id", None)
    if city_id:
        city = await City.objects.filter(id=city_id).afirst()
        if not city:
            raise RequestError(
                err_code=ErrorCode.INVALID_ENTRY,
                err_msg="Invalid Entry",
                data={"city_id": "No city with that ID"},
                status_code=422,
            )
        data["city_id"] = city_id
        user.city_name = city.name

    # Handle file upload
    image_upload_status = False
    file_type = data.pop("file_type", None)
    if file_type:
        image_upload_status = True
        avatar = user.avatar
        if avatar:
            avatar.resource_type = file_type
            await avatar.asave()
        else:
            avatar = await File.objects.acreate(resource_type=file_type)
        data["avatar"] = avatar

    # Set attributes from data to user object
    user = set_dict_attr(user, data)
    await user.asave()
    user.image_upload_status = image_upload_status
    return CustomResponse.success(message="User updated", data=user)


@profiles_router.post(
    "/profile/",
    summary="Delete user's account",
    description="This endpoint deletes a particular user's account",
    response=ResponseSchema,
    auth=AuthUser(),
)
async def delete_user(request, data: DeleteUserSchema):
    user = await request.auth

    # Check if password is valid
    if not user.check_password(data.password):
        raise RequestError(
            err_code=ErrorCode.INVALID_CREDENTIALS,
            err_msg="Invalid Entry",
            status_code=422,
            data={"password": "Incorrect password"},
        )

    # Delete user
    await user.adelete()
    return CustomResponse.success(message="User deleted")
