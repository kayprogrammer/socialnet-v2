from django.test import TestCase
from django.test.client import AsyncClient
from unittest import mock
from apps.accounts.models import User
from apps.common.utils import TestUtil
from apps.common.error import ErrorCode
from apps.profiles.models import Friend, Notification
from cities_light.models import City, Country, Region
from django.utils.text import slugify
import uuid


class TestProfile(TestCase):
    cities_url = "/api/v2/profiles/cities/"
    profile_url = "/api/v2/profiles/profile/"
    friends_url = "/api/v2/profiles/friends/"
    friend_requests_url = "/api/v2/profiles/friends/requests/"
    notifications_url = "/api/v2/profiles/notifications/"

    maxDiff = None

    def setUp(self):
        self.client = AsyncClient()
        self.content_type = "application/json"

        # user
        verified_user = TestUtil.verified_user()
        another_verified_user = TestUtil.another_verified_user()
        self.verified_user = verified_user

        # auth
        auth_token = TestUtil.auth_token(verified_user)
        self.bearer = {"Authorization": f"Bearer {auth_token}"}
        auth_token = TestUtil.auth_token(another_verified_user)
        self.other_user_bearer = {"Authorization": f"Bearer {auth_token}"}

        # city
        country = Country.objects.create(name="Test Country", continent="AF", tld="tc")
        region = Region.objects.create(
            name="Test Region", display_name="testreg", country=country
        )
        city = City.objects.create(
            name="Test City", display_name="testcit", region=region, country=country
        )
        self.city = city

        # Friend
        self.friend = Friend.objects.create(
            requester=verified_user, requestee=another_verified_user, status="ACCEPTED"
        )

    async def test_retrieve_cities(self):
        city = self.city

        # Test for valid response for non-existent city name query
        response = await self.client.get(
            f"{self.cities_url}?name=non_existent", content_type=self.content_type
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "success", "message": "No match found", "data": []},
        )

        # Test for valid response for existent city name query
        response = await self.client.get(
            f"{self.cities_url}?name={city.name}", content_type=self.content_type
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Cities Fetched",
                "data": [
                    {
                        "id": city.id,
                        "name": city.name,
                        "region": city.region.name,
                        "country": city.country.name,
                    }
                ],
            },
        )

    async def test_retrieve_profile(self):
        user = self.verified_user

        # Test for valid response for non-existent username
        response = await self.client.get(
            f"{self.profile_url}invalid_username/", content_type=self.content_type
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "message": "No user with that username",
                "code": ErrorCode.NON_EXISTENT,
            },
        )

        # Test for valid response for valid entry
        response = await self.client.get(
            f"{self.profile_url}{user.username}/", content_type=self.content_type
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "User details fetched",
                "data": {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "username": user.username,
                    "email": user.email,
                    "bio": user.bio,
                    "avatar": user.get_avatar,
                    "dob": user.dob,
                    "city": None,
                    "created_at": mock.ANY,
                    "updated_at": mock.ANY,
                },
            },
        )

    async def test_update_profile(self):
        user = self.verified_user

        user_data = {
            "first_name": "TestUpdated",
            "last_name": "VerifiedUpdated",
            "bio": "Updated my bio",
        }

        # Test for valid response for valid entry
        response = await self.client.patch(
            self.profile_url,
            user_data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "User updated",
                "data": {
                    "first_name": user_data["first_name"],
                    "last_name": user_data["last_name"],
                    "username": slugify(
                        f"{user_data['first_name']} {user_data['last_name']}"
                    ),
                    "email": user.email,
                    "bio": user_data["bio"],
                    "dob": user.dob,
                    "city": None,
                    "created_at": mock.ANY,
                    "updated_at": mock.ANY,
                    "file_upload_data": None,
                },
            },
        )

    async def test_delete_profile(self):
        user_data = {"password": "invalid_pass"}

        # Test for valid response for invalid entry
        response = await self.client.post(
            self.profile_url,
            user_data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "message": "Invalid Entry",
                "code": ErrorCode.INVALID_CREDENTIALS,
                "data": {"password": "Incorrect password"},
            },
        )

        # Test for valid response for valid entry
        user_data["password"] = "testpassword"
        response = await self.client.post(
            self.profile_url,
            user_data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "User deleted",
            },
        )

    async def test_retrieve_friends(self):
        friend = self.friend.requestee

        # Test for valid response
        response = await self.client.get(
            self.friends_url, content_type=self.content_type, **self.bearer
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Friends fetched",
                "data": {
                    "per_page": 20,
                    "current_page": 1,
                    "last_page": 1,
                    "users": [
                        {
                            "first_name": friend.first_name,
                            "last_name": friend.last_name,
                            "username": friend.username,
                            "email": friend.email,
                            "bio": friend.bio,
                            "avatar": friend.get_avatar,
                            "dob": friend.dob,
                            "city": None,
                            "created_at": mock.ANY,
                            "updated_at": mock.ANY,
                        }
                    ],
                },
            },
        )

    async def test_send_friend_request(self):
        user = await User.objects.acreate_user(
            first_name="Friend",
            last_name="User",
            email="friend_user@email.com",
            password="password",
        )

        data = {"username": "invalid_username"}

        # Test for valid response for non-existent user name
        response = await self.client.post(
            self.friend_requests_url,
            data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.NON_EXISTENT,
                "message": "User does not exist!",
            },
        )

        # Test for valid response for valid inputs
        data["username"] = user.username
        response = await self.client.post(
            self.friend_requests_url,
            data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(), {"status": "success", "message": "Friend Request sent"}
        )

        # You can test for other error responses yourself.....

    async def test_accept_or_reject_friend_request(self):
        friend = self.friend
        friend.status = "PENDING"
        await friend.asave()

        data = {"username": "invalid_username", "accepted": True}

        # Test for valid response for non-existent user name
        response = await self.client.put(
            self.friend_requests_url,
            data,
            content_type=self.content_type,
            **self.other_user_bearer,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.NON_EXISTENT,
                "message": "User does not exist!",
            },
        )

        # Test for valid response for valid inputs
        data["username"] = friend.requester.username
        response = await self.client.put(
            self.friend_requests_url,
            data,
            content_type=self.content_type,
            **self.other_user_bearer,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"status": "success", "message": "Friend Request Accepted"}
        )

        # You can test for other error responses yourself.....

    async def test_retrieve_notifications(self):
        notification = await Notification.objects.acreate(
            ntype="ADMIN", text="A new update is coming!"
        )
        await notification.receivers.aadd(self.verified_user)

        # Test for valid response
        response = await self.client.get(
            self.notifications_url, content_type=self.content_type, **self.bearer
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Notifications fetched",
                "data": {
                    "per_page": 50,
                    "current_page": 1,
                    "last_page": 1,
                    "notifications": [
                        {
                            "id": str(notification.id),
                            "sender": None,
                            "ntype": notification.ntype,
                            "message": notification.message,
                            "post_slug": None,
                            "comment_slug": None,
                            "reply_slug": None,
                            "is_read": False,
                        }
                    ],
                },
            },
        )

    async def test_read_notification(self):
        notification = await Notification.objects.acreate(
            ntype="ADMIN", text="A new update is coming!"
        )
        await notification.receivers.aadd(self.verified_user)

        data = {"id": uuid.uuid4(), "mark_all_as_read": False}

        # Test for invalid response for non-existent id
        response = await self.client.post(
            self.notifications_url,
            data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.NON_EXISTENT,
                "message": "User has no notification with that ID",
            },
        )

        # Test for valid response for valid inputs
        data["id"] = notification.id
        response = await self.client.post(
            self.notifications_url,
            data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"status": "success", "message": "Notification read"}
        )
