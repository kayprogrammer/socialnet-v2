from typing import Optional
from django.db.models import Q, Case, When, Value, BooleanField, F
from ninja.router import Router
from apps.accounts.models import User
from apps.common.paginators import CustomPagination
from apps.common.responses import CustomResponse
from apps.common.utils import AuthUser
from asgiref.sync import sync_to_async

from apps.profiles.schemas import CitiesResponseSchema, ProfilesResponseSchema
from cities_light.models import City
import re

profiles_router = Router(tags=["Profiles"])

paginator = CustomPagination()


def get_users_queryset(current_user):
    users = User.objects.select_related("avatar", "city")
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
