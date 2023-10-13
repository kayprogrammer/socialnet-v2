from django.db.models import Q, Case, When, Value, BooleanField
from ninja.router import Router
from apps.accounts.models import User
from apps.common.paginators import CustomPagination
from apps.common.responses import CustomResponse
from apps.common.utils import AuthUser
from asgiref.sync import sync_to_async

from apps.profiles.schemas import ProfilesResponseSchema

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
    users = get_users_queryset(user)
    paginated_users = (await paginator.paginate_queryset(users, page))["items"]
    print(paginated_users)
    return CustomResponse.success(message="Users fetched", data=paginated_users)
