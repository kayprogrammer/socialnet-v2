from ninja.security import HttpBearer
from apps.accounts.auth import Authentication
from apps.accounts.models import User
from apps.common.error import ErrorCode
from apps.common.exceptions import RequestError


class AuthUser(HttpBearer):
    async def authenticate(self, request, token):
        if not token:
            raise RequestError(
                err_code=ErrorCode.INVALID_AUTH,
                err_msg="Auth Bearer not provided!",
                status_code=401,
            )

        user = await Authentication.decodeAuthorization(token)
        if not user:
            raise RequestError(
                err_code=ErrorCode.INVALID_TOKEN,
                err_msg="Auth Token is Invalid or Expired!",
                status_code=401,
            )
        return user


def set_dict_attr(obj, data):
    for attr, value in data.items():
        setattr(obj, attr, value)
    return obj


# Test Utils
class TestUtil:
    def new_user():
        user_dict = {
            "first_name": "Test",
            "last_name": "Name",
            "email": "test@example.com",
            "password": "testpassword",
        }
        user = User.objects.create_user(**user_dict)
        return user

    def verified_user():
        user_dict = {
            "first_name": "Test",
            "last_name": "Verified",
            "email": "testverifieduser@example.com",
            "is_email_verified": True,
            "password": "testpassword",
        }
        user = User.objects.create_user(**user_dict)
        return user

    def another_verified_user():
        create_user_dict = {
            "first_name": "AnotherTest",
            "last_name": "UserVerified",
            "email": "anothertestverifieduser@example.com",
            "is_email_verified": True,
            "password": "anothertestverifieduser123",
        }
        user = User.objects.create_user(**create_user_dict)
        return user

    def auth_token(verified_user):
        access = Authentication.create_access_token(
            {"user_id": str(verified_user.id), "username": verified_user.username}
        )
        refresh = Authentication.create_refresh_token()
        verified_user.access = access
        verified_user.refresh = refresh
        verified_user.save()
        return access
