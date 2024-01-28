from django.test import TestCase
from django.test.client import AsyncClient
from apps.accounts.auth import Authentication
from apps.common.utils import TestUtil
from apps.accounts.models import Otp
from unittest import mock

from apps.common.error import ErrorCode


class TestAccounts(TestCase):
    register_url = "/api/v2/auth/register/"
    verify_email_url = "/api/v2/auth/verify-email/"
    resend_verification_email_url = "/api/v2/auth/resend-verification-email/"
    send_password_reset_otp_url = "/api/v2/auth/send-password-reset-otp/"
    set_new_password_url = "/api/v2/auth/set-new-password/"
    login_url = "/api/v2/auth/login/"
    refresh_url = "/api/v2/auth/refresh/"
    logout_url = "/api/v2/auth/logout/"

    def setUp(self):
        self.client = AsyncClient()
        self.content_type = "application/json"
        self.new_user = TestUtil.new_user()
        verified_user = TestUtil.verified_user()
        self.verified_user = verified_user
        self.auth_token = TestUtil.auth_token(verified_user)

    async def test_register(self):
        email = "testregisteruser@example.com"
        password = "testregisteruserpassword"
        user_in = {
            "first_name": "Testregister",
            "last_name": "User",
            "email": email,
            "password": password,
            "terms_agreement": True,
        }

        # Verify that a new user can be registered successfully
        mock.patch("apps.accounts.emails.Util", new="")
        response = await self.client.post(
            self.register_url, user_in, content_type=self.content_type
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Registration successful",
                "data": {"email": user_in["email"]},
            },
        )

        # Verify that a user with the same email cannot be registered again
        mock.patch("apps.accounts.emails.Util", new="")
        response = await self.client.post(
            self.register_url, user_in, content_type=self.content_type
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.INVALID_ENTRY,
                "message": "Invalid Entry",
                "data": {"email": "Email already registered!"},
            },
        )

    async def test_verify_email(self):
        new_user = self.new_user
        otp = "111111"
        # Verify that the email verification fails with an invalid otp
        response = await self.client.post(
            self.verify_email_url,
            {"email": new_user.email, "otp": otp},
            content_type=self.content_type,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.INCORRECT_OTP,
                "message": "Incorrect Otp",
            },
        )

        # Verify that the email verification succeeds with a valid otp
        otp = await Otp.objects.acreate(user_id=new_user.id, code=otp)
        mock.patch("apps.accounts.emails.Util", new="")
        response = await self.client.post(
            self.verify_email_url,
            {"email": new_user.email, "otp": otp.code},
            content_type=self.content_type,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "success", "message": "Account verification successful"},
        )

    async def test_resend_verification_email(self):
        new_user = self.new_user
        user_in = {"email": new_user.email}

        # Verify that an unverified user can get a new email
        mock.patch("apps.accounts.emails.Util", new="")
        # Then, attempt to resend the verification email
        response = await self.client.post(
            self.resend_verification_email_url, user_in, content_type=self.content_type
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"status": "success", "message": "Verification email sent"}
        )

        # Verify that a verified user cannot get a new email
        new_user.is_email_verified = True
        await new_user.asave()
        mock.patch("apps.accounts.emails.Util", new="")
        response = await self.client.post(
            self.resend_verification_email_url,
            {"email": new_user.email},
            content_type=self.content_type,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"status": "success", "message": "Email already verified"}
        )

        # Verify that an error is raised when attempting to resend the verification email for a user that doesn't exist
        mock.patch("apps.accounts.emails.Util", new="")
        response = await self.client.post(
            self.resend_verification_email_url,
            {"email": "invalid@example.com"},
            content_type=self.content_type,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.INCORRECT_EMAIL,
                "message": "Incorrect Email",
            },
        )

    async def test_get_password_otp(self):
        verified_user = self.verified_user
        email = verified_user.email

        password = "testverifieduser123"
        user_dict = {"email": email, "password": password}

        mock.patch("apps.accounts.emails.Util", new="")
        # Then, attempt to get password reset token
        response = await self.client.post(
            self.send_password_reset_otp_url, user_dict, content_type=self.content_type
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "success", "message": "Password otp sent"},
        )

        # Verify that an error is raised when attempting to get password reset token for a user that doesn't exist
        mock.patch("apps.accounts.emails.Util", new="")
        response = await self.client.post(
            self.send_password_reset_otp_url,
            {"email": "invalid@example.com"},
            content_type=self.content_type,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.INCORRECT_EMAIL,
                "message": "Incorrect Email",
            },
        )

    async def test_reset_password(self):
        verified_user = self.verified_user
        password_reset_data = {
            "email": verified_user.email,
            "password": "newtestverifieduserpassword123",
        }
        otp = "111111"

        # Verify that the password reset verification fails with an incorrect email
        response = await self.client.post(
            self.set_new_password_url,
            {
                "email": "invalidemail@example.com",
                "otp": otp,
                "password": "newpassword",
            },
            content_type=self.content_type,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.INCORRECT_EMAIL,
                "message": "Incorrect Email",
            },
        )

        # Verify that the password reset verification fails with an invalid otp
        password_reset_data["otp"] = otp
        response = await self.client.post(
            self.set_new_password_url,
            password_reset_data,
            content_type=self.content_type,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.INCORRECT_OTP,
                "message": "Incorrect Otp",
            },
        )

        # Verify that password reset succeeds
        await Otp.objects.acreate(user_id=verified_user.id, code=otp)
        password_reset_data["otp"] = otp
        mock.patch("apps.accounts.emails.Util", new="")
        response = await self.client.post(
            self.set_new_password_url,
            password_reset_data,
            content_type=self.content_type,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "success", "message": "Password reset successful"},
        )

    async def test_login(self):
        new_user = self.new_user

        # Test for invalid credentials
        response = await self.client.post(
            self.login_url,
            {"email": "invalid@email.com", "password": "invalidpassword"},
            content_type=self.content_type,
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.INVALID_CREDENTIALS,
                "message": "Invalid credentials",
            },
        )

        # Test for unverified credentials (email)
        response = await self.client.post(
            self.login_url,
            {"email": new_user.email, "password": "testpassword"},
            content_type=self.content_type,
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.UNVERIFIED_USER,
                "message": "Verify your email first",
            },
        )

        # Test for valid credentials and verified email address
        new_user.is_email_verified = True
        await new_user.asave()
        response = await self.client.post(
            self.login_url,
            {"email": new_user.email, "password": "testpassword"},
            content_type=self.content_type,
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Login successful",
                "data": {"access": mock.ANY, "refresh": mock.ANY},
            },
        )

    async def test_refresh_token(self):
        verified_user = self.verified_user

        # Test for invalid refresh token
        response = await self.client.post(
            self.refresh_url,
            {"refresh": "invalid_refresh_token"},
            content_type=self.content_type,
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.INVALID_TOKEN,
                "message": "Refresh token is invalid or expired",
            },
        )

        # Test for valid refresh token
        refresh = Authentication.create_refresh_token()
        verified_user.refresh = refresh
        await verified_user.asave()
        mock.patch("apps.accounts.auth.Authentication.decode_jwt", return_value=True)
        response = await self.client.post(
            self.refresh_url, {"refresh": refresh}, content_type=self.content_type
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Tokens refresh successful",
                "data": {"access": mock.ANY, "refresh": mock.ANY},
            },
        )

    async def test_logout(self):
        # Ensures if authorized user logs out successfully
        bearer = {"Authorization": f"Bearer {self.auth_token}"}
        response = await self.client.get(
            self.logout_url, content_type=self.content_type, **bearer
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "success", "message": "Logout successful"},
        )

        # Ensures if unauthorized user cannot log out
        bearer = {"Authorization": "invalid_token"}
        response = await self.client.get(
            self.logout_url, content_type=self.content_type, **bearer
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.INVALID_AUTH,
                "message": "Unauthorized User",
            },
        )
