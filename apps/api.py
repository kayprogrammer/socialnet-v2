from django.conf import settings
from ninja import NinjaAPI
from ninja.responses import Response
from ninja.errors import ValidationError, AuthenticationError
from apps.common.error import ErrorCode
from apps.common.exceptions import RequestError, request_errors, validation_errors
from apps.common.schemas import ResponseSchema

from apps.general.views import general_router
from apps.accounts.views import auth_router
from apps.profiles.views import profiles_router
from apps.feed.views import feed_router
from apps.chat.views import chats_router


api = NinjaAPI(
    title=settings.SITE_NAME,
    description="A Social Networking API built with Django Ninja",
    version="2.0.0",
    docs_url="/",
)

api.add_router("/api/v2/general/", general_router)
api.add_router("/api/v2/auth/", auth_router)
api.add_router("/api/v2/profiles/", profiles_router)
api.add_router("/api/v2/feed/", feed_router)
api.add_router("/api/v2/chats/", chats_router)


@api.get(
    "/api/v2/healthcheck/",
    summary="API Health Check",
    description="This endpoint checks the health of the API",
    response=ResponseSchema,
    tags=["HealthCheck"],
)
async def get(request):
    return {"message": "pong"}


@api.exception_handler(ValidationError)
def validation_exc_handler(request, exc):
    return validation_errors(exc)


@api.exception_handler(RequestError)
def request_exc_handler(request, exc):
    return request_errors(exc)


@api.exception_handler(AuthenticationError)
def request_exc_handler(request, exc):
    if request.resolver_match.url_name == "retrieve_users":
        request.auth = None
        return None
    return Response(
        {
            "status": "failure",
            "code": ErrorCode.INVALID_AUTH,
            "message": "Unauthorized User",
        },
        status=401,
    )
