from ninja import Router
from apps.common.error import ErrorCode
from apps.common.responses import CustomResponse
from apps.common.utils import AuthUser

from apps.common.schemas import ResponseSchema
from .schemas import (
    LoginUserSchema,
    RefreshTokensSchema,
    RegisterResponseSchema,
    RegisterUserSchema,
    RequestOtpSchema,
    SetNewPasswordSchema,
    TokensResponseSchema,
    VerifyOtpSchema,
)

from .auth import Authentication
from .emails import Util

from .models import Otp, User

from apps.common.exceptions import RequestError

auth_router = Router(tags=["Auth"])


@auth_router.post(
    "/register/",
    summary="Register a new user",
    description="This endpoint registers new users into our application",
    response={201: RegisterResponseSchema},
)
async def register(request, data: RegisterUserSchema):
    # Check for existing user
    existing_user = await User.objects.aget_or_none(email=data.email)
    if existing_user:
        raise RequestError(
            err_code=ErrorCode.INVALID_ENTRY,
            err_msg="Invalid Entry",
            status_code=422,
            data={"email": "Email already registered!"},
        )

    # Create user
    user = await User.objects.acreate_user(**data.dict())

    # Send verification email
    await Util.send_activation_otp(user)

    return CustomResponse.success(
        message="Registration successful", data={"email": data.email}
    )


@auth_router.post(
    "/verify-email/",
    summary="Verify a user's email",
    description="This endpoint verifies a user's email",
    response=ResponseSchema,
)
async def verify_email(request, data: VerifyOtpSchema):
    email = data.email
    otp_code = data.otp

    user = await User.objects.aget_or_none(email=email)

    if not user:
        raise RequestError(
            err_code=ErrorCode.INCORRECT_EMAIL,
            err_msg="Incorrect Email",
            status_code=404,
        )

    if user.is_email_verified:
        return CustomResponse.success(message="Email already verified")

    otp = await Otp.objects.aget_or_none(user=user)
    if not otp or otp.code != otp_code:
        raise RequestError(
            err_code=ErrorCode.INCORRECT_OTP, err_msg="Incorrect Otp", status_code=404
        )
    if otp.check_expiration():
        raise RequestError(
            err_code=ErrorCode.EXPIRED_OTP, err_msg="Expired Otp", status_code=498
        )

    user.is_email_verified = True
    await user.asave()
    await otp.adelete()

    # Send welcome email
    Util.welcome_email(user)
    return CustomResponse.success(
        message="Account verification successful", status_code=200
    )


@auth_router.post(
    "/resend-verification-email/",
    summary="Resend Verification Email",
    description="This endpoint resends new otp to the user's email",
    response=ResponseSchema,
)
async def resend_verification_email(request, data: RequestOtpSchema):
    email = data.email
    user = await User.objects.aget_or_none(email=email)
    if not user:
        raise RequestError(
            err_code=ErrorCode.INCORRECT_EMAIL,
            err_msg="Incorrect Email",
            status_code=404,
        )
    if user.is_email_verified:
        return CustomResponse.success(message="Email already verified")

    # Send verification email
    await Util.send_activation_otp(user)
    return CustomResponse.success(message="Verification email sent", status_code=200)


@auth_router.post(
    "/send-password-reset-otp/",
    summary="Send Password Reset Otp",
    description="This endpoint sends new password reset otp to the user's email",
    response=ResponseSchema,
)
async def send_password_reset_otp(request, data: RequestOtpSchema):
    email = data.email

    user = await User.objects.aget_or_none(email=email)
    if not user:
        raise RequestError(
            err_code=ErrorCode.INCORRECT_EMAIL,
            err_msg="Incorrect Email",
            status_code=404,
        )

    # Send password reset email
    await Util.send_password_change_otp(user)
    return CustomResponse.success(message="Password otp sent")


@auth_router.post(
    "/set-new-password/",
    summary="Set New Password",
    description="This endpoint verifies the password reset otp",
    response=ResponseSchema,
)
async def set_new_password(request, data: SetNewPasswordSchema):
    email = data.email
    code = data.otp
    password = data.password

    user = await User.objects.aget_or_none(email=email)
    if not user:
        raise RequestError(
            err_code=ErrorCode.INCORRECT_EMAIL,
            err_msg="Incorrect Email",
            status_code=404,
        )

    otp = await Otp.objects.aget_or_none(user=user)
    if not otp or otp.code != code:
        raise RequestError(
            err_code=ErrorCode.INCORRECT_OTP,
            err_msg="Incorrect Otp",
            status_code=404,
        )

    if otp.check_expiration():
        raise RequestError(
            err_code=ErrorCode.EXPIRED_OTP, err_msg="Expired Otp", status_code=498
        )

    user.set_password(password)
    await user.asave()

    # Send password reset success email
    Util.password_reset_confirmation(user)
    return CustomResponse.success(message="Password reset successful")


@auth_router.post(
    "/login/",
    summary="Login a user",
    description="This endpoint generates new access and refresh tokens for authentication",
    response={201: TokensResponseSchema},
)
async def login(request, data: LoginUserSchema):
    email = data.email
    password = data.password

    user = await User.objects.aget_or_none(email=email)
    if not user or not user.check_password(password):
        raise RequestError(
            err_code=ErrorCode.INVALID_CREDENTIALS,
            err_msg="Invalid credentials",
            status_code=401,
        )

    if not user.is_email_verified:
        raise RequestError(
            err_code=ErrorCode.UNVERIFIED_USER,
            err_msg="Verify your email first",
            status_code=401,
        )

    # Create tokens and store in jwt model
    access = Authentication.create_access_token(
        {"user_id": str(user.id), "username": user.username}
    )
    refresh = Authentication.create_refresh_token()
    user.access = access
    user.refresh = refresh
    await user.asave()

    return CustomResponse.success(
        message="Login successful",
        data={"access": access, "refresh": refresh},
        status_code=201,
    )


@auth_router.post(
    "/refresh/",
    summary="Refresh tokens",
    description="This endpoint refresh tokens by generating new access and refresh tokens for a user",
    response={201: TokensResponseSchema},
)
async def refresh(request, data: RefreshTokensSchema):
    token = data.refresh
    user = await User.objects.aget_or_none(refresh=token)

    if not user or not Authentication.decode_jwt(token):
        raise RequestError(
            err_code=ErrorCode.INVALID_TOKEN,
            err_msg="Refresh token is invalid or expired",
            status_code=401,
        )

    access = Authentication.create_access_token(
        {"user_id": str(user.id), "username": user.username}
    )
    refresh = Authentication.create_refresh_token()

    user.access = access
    user.refresh = refresh
    await user.asave()

    return CustomResponse.success(
        message="Tokens refresh successful",
        data={"access": access, "refresh": refresh},
        status_code=201,
    )


@auth_router.get(
    "/logout/",
    summary="Logout a user",
    description="This endpoint logs a user out from our application",
    response=ResponseSchema,
    auth=AuthUser(),
)
async def logout(request):
    user = await request.auth
    user.access = None
    user.refresh = None
    await user.asave()
    return CustomResponse.success(message="Logout successful")
