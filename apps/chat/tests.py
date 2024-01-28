from django.test import TestCase
from django.test.client import AsyncClient
from unittest import mock
from apps.chat.models import Chat, Message
from apps.common.schemas import UserDataSchema
from apps.common.utils import TestUtil
from apps.common.error import ErrorCode
import uuid


class TestChat(TestCase):
    chats_url = "/api/v2/chats/"
    messages_url = "/api/v2/chats/messages/"
    groups_url = "/api/v2/chats/groups/group/"

    maxDiff = None

    def setUp(self):
        self.client = AsyncClient()
        self.content_type = "application/json"

        # user
        verified_user = TestUtil.verified_user()
        another_verified_user = TestUtil.another_verified_user()
        self.verified_user = verified_user
        self.another_verified_user = another_verified_user

        # chat & message
        chat = Chat.objects.create(owner=verified_user)
        chat.users.add(another_verified_user)
        message = Message.objects.create(
            chat=chat, sender=verified_user, text="Hello Boss"
        )
        group_chat = Chat.objects.create(
            name="My New Group",
            owner=verified_user,
            ctype="GROUP",
            description="This is the description of my group chat",
        )
        group_chat.users.add(another_verified_user)
        self.chat = chat
        self.message = message
        self.group_chat = group_chat

        # auth
        auth_token = TestUtil.auth_token(verified_user)
        self.bearer = {"Authorization": f"Bearer {auth_token}"}
        auth_token = TestUtil.auth_token(another_verified_user)
        self.other_user_bearer = {"Authorization": f"Bearer {auth_token}"}

    async def test_retrieve_chats(self):
        response = await self.client.get(
            self.chats_url, content_type=self.content_type, **self.bearer
        )
        self.assertEqual(response.status_code, 200)
        resp = response.json()
        self.assertEqual(resp["status"], "success")
        self.assertEqual(resp["message"], "Chats fetched")
        self.assertTrue(len(resp["data"]["chats"]) > 0)

    async def test_send_message(self):
        chat = self.chat
        message_data = {"chat_id": uuid.uuid4(), "text": "JESUS is KING"}

        # Verify the requests fails with invalid chat id
        response = await self.client.post(
            self.chats_url,
            message_data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.NON_EXISTENT,
                "message": "User has no chat with that ID",
            },
        )

        # Verify the requests suceeds with valid chat id
        message_data["chat_id"] = chat.id
        response = await self.client.post(
            self.chats_url,
            message_data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Message sent",
                "data": {
                    "id": mock.ANY,
                    "chat_id": str(chat.id),
                    "sender": mock.ANY,
                    "text": message_data["text"],
                    "created_at": mock.ANY,
                    "updated_at": mock.ANY,
                    "file_upload_data": None,
                },
            },
        )

        # You can test for other error responses yourself

    async def test_retrieve_chat_messages(self):
        chat = self.chat
        message = self.message
        other_user = self.another_verified_user

        # Verify the request fails with invalid chat ID
        response = await self.client.get(
            f"{self.chats_url}{uuid.uuid4()}/",
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.NON_EXISTENT,
                "message": "User has no chat with that ID",
            },
        )

        # Verify the request succeeds with valid chat ID
        response = await self.client.get(
            f"{self.chats_url}{chat.id}/", content_type=self.content_type, **self.bearer
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Messages fetched",
                "data": {
                    "chat": {
                        "id": str(chat.id),
                        "name": chat.name,
                        "owner": mock.ANY,
                        "ctype": chat.ctype,
                        "description": chat.description,
                        "image": chat.get_image,
                        "latest_message": {
                            "sender": mock.ANY,
                            "text": message.text,
                            "file": message.get_file,
                        },
                        "created_at": mock.ANY,
                        "updated_at": mock.ANY,
                    },
                    "messages": {
                        "per_page": 400,
                        "current_page": 1,
                        "last_page": 1,
                        "items": [
                            {
                                "id": str(message.id),
                                "chat_id": str(chat.id),
                                "sender": mock.ANY,
                                "text": message.text,
                                "file": message.get_file,
                                "created_at": mock.ANY,
                                "updated_at": mock.ANY,
                            }
                        ],
                    },
                    "users": [UserDataSchema.from_orm(other_user).dict()],
                },
            },
        )

    async def test_update_group_chat(self):
        chat = self.group_chat
        other_user = self.another_verified_user
        chat_data = {
            "name": "Updated Group chat name",
            "description": "Updated group chat description",
        }

        # Verify the requests fails with invalid chat id
        response = await self.client.patch(
            f"{self.chats_url}{uuid.uuid4()}/",
            chat_data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.NON_EXISTENT,
                "message": "User owns no group chat with that ID",
            },
        )

        # Verify the requests suceeds with valid chat id
        response = await self.client.patch(
            f"{self.chats_url}{chat.id}/",
            chat_data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Chat updated",
                "data": {
                    "id": str(chat.id),
                    "name": chat_data["name"],
                    "description": chat_data["description"],
                    "users": [UserDataSchema.from_orm(other_user).dict()],
                    "file_upload_data": None,
                },
            },
        )

        # You can test for other error responses yourself

    async def test_delete_group_chat(self):
        chat = self.group_chat

        # Verify the requests fails with invalid chat id
        response = await self.client.delete(
            f"{self.chats_url}{uuid.uuid4()}/",
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.NON_EXISTENT,
                "message": "User owns no group chat with that ID",
            },
        )

        # Verify the requests suceeds with valid chat id
        response = await self.client.delete(
            f"{self.chats_url}{chat.id}/", content_type=self.content_type, **self.bearer
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Group Chat Deleted",
            },
        )

    async def test_update_message(self):
        message = self.message
        message_data = {
            "text": "Jesus is Lord",
        }

        # Verify the requests fails with invalid message id
        response = await self.client.put(
            f"{self.messages_url}{uuid.uuid4()}/",
            message_data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.NON_EXISTENT,
                "message": "User has no message with that ID",
            },
        )

        # Verify the requests suceeds with valid message id
        response = await self.client.put(
            f"{self.messages_url}{message.id}/",
            message_data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Message updated",
                "data": {
                    "id": str(message.id),
                    "chat_id": str(message.chat.id),
                    "sender": mock.ANY,
                    "text": message_data["text"],
                    "created_at": mock.ANY,
                    "updated_at": mock.ANY,
                    "file_upload_data": None,
                },
            },
        )

    async def test_delete_message(self):
        message = self.message

        # Verify the requests fails with invalid message id
        response = await self.client.delete(
            f"{self.messages_url}{uuid.uuid4()}/",
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.NON_EXISTENT,
                "message": "User has no message with that ID",
            },
        )

        # Verify the requests suceeds with valid message id
        response = await self.client.delete(
            f"{self.messages_url}{message.id}/",
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Message deleted",
            },
        )

    async def test_create_group_chat(self):
        other_user = self.another_verified_user
        chat_data = {
            "name": "New Group Chat",
            "description": "JESUS is KING",
            "usernames_to_add": ["invalid_username"],
        }

        # Verify the requests fails with invalid username id
        response = await self.client.post(
            self.groups_url,
            chat_data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.INVALID_ENTRY,
                "message": "Invalid Entry",
                "data": {"usernames_to_add": "Enter at least one valid username"},
            },
        )

        # Verify the requests suceeds with valid chat id
        chat_data["usernames_to_add"] = [other_user.username]
        response = await self.client.post(
            self.groups_url,
            chat_data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Chat created",
                "data": {
                    "id": mock.ANY,
                    "name": chat_data["name"],
                    "description": chat_data["description"],
                    "users": [UserDataSchema.from_orm(other_user).dict()],
                    "file_upload_data": None,
                },
            },
        )
