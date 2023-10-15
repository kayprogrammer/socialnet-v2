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
from apps.profiles.models import Friend

from apps.profiles.schemas import (
    AcceptFriendRequestSchema,
    CitiesResponseSchema,
    DeleteUserSchema,
    ProfileResponseSchema,
    ProfileUpdateResponseSchema,
    ProfileUpdateSchema,
    ProfilesResponseSchema,
    SendFriendRequestSchema,
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
    user.city_name = user.city.name if user.city else None
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


@profiles_router.get(
    "/friends/",
    summary="Retrieve Friends",
    description="This endpoint retrieves friends of a user",
    response=ProfilesResponseSchema,
    auth=AuthUser(),
)
async def retrieve_friends(request, page: int = 1):
    user = await request.auth
    friends = (
        Friend.objects.filter(Q(requester=user) | Q(requestee=user))
        .filter(status="ACCEPTED")
        .select_related("requester", "requestee")
    )
    friend_ids = friends.annotate(
        friend_id=Case(
            When(requester=user, then=F("requestee")),
            When(requestee=user, then=F("requester")),
        )
    ).values_list("friend_id", flat=True)
    friends = (
        User.objects.filter(id__in=friend_ids)
        .annotate(city_name=F("city__name"))
        .select_related("avatar")
    )

    # Return paginated data
    paginator.page_size = 20
    paginated_data = await paginator.paginate_queryset(friends, page)
    return CustomResponse.success(message="Friends fetched", data=paginated_data)


@profiles_router.get(
    "/friends/requests/",
    summary="Retrieve Friend Requests",
    description="This endpoint retrieves friend requests of a user",
    response=ProfilesResponseSchema,
    auth=AuthUser(),
)
async def retrieve_friend_requests(request, page: int = 1):
    user = await request.auth
    friend_ids = Friend.objects.filter(
        requestee_id=user.id, status="PENDING"
    ).values_list("requester_id", flat=True)
    friends = (
        User.objects.filter(id__in=friend_ids)
        .annotate(city_name=F("city__name"))
        .select_related("avatar")
    )

    # Return paginated data
    paginator.page_size = 20
    paginated_data = await paginator.paginate_queryset(friends, page)
    return CustomResponse.success(
        message="Friend Requests fetched", data=paginated_data
    )


async def get_other_user_and_friend(user, username, status=None):
    # Get and validate username existence
    other_user = await User.objects.aget_or_none(username=username)
    if not other_user:
        raise RequestError(
            err_code=ErrorCode.NON_EXISTENT,
            err_msg="User does not exist!",
            status_code=404,
        )

    friend = Friend.objects.filter(
        Q(requester=user, requestee=other_user)
        | Q(requester=other_user, requestee=user)
    )
    if status:
        friend = friend.filter(status=status)
    friend = await friend.aget_or_none()
    return other_user, friend


@profiles_router.post(
    "/friends/",
    summary="Send Or Delete Friend Request",
    description="This endpoint sends or delete friend requests",
    response={201: ResponseSchema, 200: ResponseSchema},
    auth=AuthUser(),
)
async def send_or_delete_friend_request(request, data: SendFriendRequestSchema):
    user = await request.auth

    other_user, friend = await get_other_user_and_friend(user, data.username)
    message = "Friend Request sent"
    status_code = 201
    if friend:
        status_code = 200
        message = "Friend Request removed"
        if user.id != friend.requester_id:
            raise RequestError(
                err_code=ErrorCode.NOT_ALLOWED,
                err_msg="The user already sent you a friend request!",
                status_code=403,
            )

        await friend.adelete()
    else:
        await Friend.objects.acreate(requester=user, requestee=other_user)

    return CustomResponse.success(message=message, status_code=status_code)


@profiles_router.put(
    "/friends/",
    summary="Accept Or Reject a Friend Request",
    description="""
        This endpoint accepts or reject a friend request
        accepted choices:
        - true - accepted
        - false - rejected
    """,
    response=ResponseSchema,
    auth=AuthUser(),
)
async def accept_or_reject_friend_request(request, data: AcceptFriendRequestSchema):
    user = await request.auth
    _, friend = await get_other_user_and_friend(user, data.username, "PENDING")
    if not friend:
        raise RequestError(
            err_code=ErrorCode.NON_EXISTENT,
            err_msg="No pending friend request exist between you and that user",
            status_code=401,
        )
    if friend.requester_id == user.id:
        raise RequestError(
            err_code=ErrorCode.NOT_ALLOWED,
            err_msg="You cannot accept or reject a friend request you sent ",
            status_code=403,
        )

    # Update or delete friend request based on status
    accepted = data.accepted
    if accepted:
        msg = "Accepted"
        friend.status = "ACCEPTED"
        await friend.asave()
    else:
        msg = "Rejected"
        await friend.adelete()

    return CustomResponse.success(message=f"Friend Request {msg}", status_code=200)
