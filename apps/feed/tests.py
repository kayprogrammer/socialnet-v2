from django.test import TestCase
from django.test.client import AsyncClient
from unittest import mock
from apps.feed.models import Post, Reaction, Comment, Reply
from apps.common.utils import TestUtil
from apps.common.error import ErrorCode
import uuid


class TestFeed(TestCase):
    posts_url = "/api/v2/feed/posts/"
    reactions_url = "/api/v2/feed/reactions/"
    comment_url = "/api/v2/feed/comments/"
    reply_url = "/api/v2/feed/replies/"

    maxDiff = None

    def setUp(self):
        self.client = AsyncClient()
        self.content_type = "application/json"

        # user
        verified_user = TestUtil.verified_user()
        another_verified_user = TestUtil.another_verified_user()
        self.verified_user = verified_user

        # post
        post = Post.objects.create(
            author=verified_user, text="This is a nice new platform"
        )
        self.post = post

        # auth
        auth_token = TestUtil.auth_token(verified_user)
        self.bearer = {"Authorization": f"Bearer {auth_token}"}
        auth_token = TestUtil.auth_token(another_verified_user)
        self.other_user_bearer = {"Authorization": f"Bearer {auth_token}"}

        # reaction
        self.reaction = Reaction.objects.create(
            user=verified_user, rtype="LIKE", post=post
        )

        # comment
        comment = Comment.objects.create(
            author=verified_user, post=post, text="Just a comment"
        )
        self.comment = comment

        # reply
        self.reply = Reply.objects.create(
            author=verified_user, comment=comment, text="Simple reply"
        )

    async def test_retrieve_posts(self):
        post = self.post
        response = await self.client.get(self.posts_url, content_type=self.content_type)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Posts fetched",
                "data": {
                    "per_page": 50,
                    "current_page": 1,
                    "last_page": 1,
                    "posts": [
                        {
                            "author": mock.ANY,
                            "text": post.text,
                            "slug": post.slug,
                            "reactions_count": mock.ANY,
                            "comments_count": mock.ANY,
                            "image": None,
                            "created_at": mock.ANY,
                            "updated_at": mock.ANY,
                        }
                    ],
                },
            },
        )

    async def test_create_post(self):
        post_dict = {"text": "My new Post"}
        response = await self.client.post(
            self.posts_url, post_dict, content_type=self.content_type, **self.bearer
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Post created",
                "data": {
                    "author": mock.ANY,
                    "text": post_dict["text"],
                    "slug": mock.ANY,
                    "created_at": mock.ANY,
                    "updated_at": mock.ANY,
                    "file_upload_data": None,
                },
            },
        )

    async def test_retrieve_post(self):
        post = self.post

        # Test for post with invalid slug
        response = await self.client.get(
            f"{self.posts_url}invalid-slug/", content_type=self.content_type
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.NON_EXISTENT,
                "message": "Post does not exist",
            },
        )

        # Test for post with valid slug
        response = await self.client.get(
            f"{self.posts_url}{post.slug}/", content_type=self.content_type
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Post Detail fetched",
                "data": {
                    "author": mock.ANY,
                    "text": post.text,
                    "slug": post.slug,
                    "reactions_count": mock.ANY,
                    "comments_count": mock.ANY,
                    "image": None,
                    "created_at": mock.ANY,
                    "updated_at": mock.ANY,
                },
            },
        )

    async def test_update_post(self):
        post_dict = {"text": "Post Text Updated"}
        post = self.post
        # Check if endpoint fails for invalid post
        response = await self.client.put(
            f"{self.posts_url}invalid-slug/",
            post_dict,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.NON_EXISTENT,
                "message": "Post does not exist",
            },
        )

        # Check if endpoint fails for invalid owner
        response = await self.client.put(
            f"{self.posts_url}{post.slug}/",
            post_dict,
            content_type=self.content_type,
            **self.other_user_bearer,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.INVALID_OWNER,
                "message": "This Post isn't yours",
            },
        )

        # Check if endpoint succeeds if all requirements are met
        response = await self.client.put(
            f"{self.posts_url}{post.slug}/",
            post_dict,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Post updated",
                "data": {
                    "author": mock.ANY,
                    "text": post_dict["text"],
                    "slug": mock.ANY,
                    "created_at": mock.ANY,
                    "updated_at": mock.ANY,
                    "file_upload_data": None,
                },
            },
        )

    async def test_delete_post(self):
        post = self.post
        # Check if endpoint fails for invalid post
        response = await self.client.delete(
            f"{self.posts_url}invalid-slug/",
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.NON_EXISTENT,
                "message": "Post does not exist",
            },
        )

        # Check if endpoint fails for invalid owner
        response = await self.client.delete(
            f"{self.posts_url}{post.slug}/",
            content_type=self.content_type,
            **self.other_user_bearer,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "code": ErrorCode.INVALID_OWNER,
                "message": "This Post isn't yours",
            },
        )

        # Check if endpoint succeeds if all requirements are met
        response = await self.client.delete(
            f"{self.posts_url}{post.slug}/",
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Post deleted",
            },
        )

    async def test_retrieve_reactions(self):
        post = self.post
        user = self.verified_user
        reaction = self.reaction

        # Test for invalid focus_value
        response = await self.client.get(
            f"{self.reactions_url}invalid_focus/{post.slug}/",
            content_type=self.content_type,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "message": "Invalid 'focus' value",
                "code": ErrorCode.INVALID_VALUE,
            },
        )

        # Test for invalid slug
        response = await self.client.get(
            f"{self.reactions_url}POST/invalid_slug/", content_type=self.content_type
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "message": "Post does not exist",
                "code": ErrorCode.NON_EXISTENT,
            },
        )

        # Test for valid values
        response = await self.client.get(
            f"{self.reactions_url}POST/{post.slug}/", content_type=self.content_type
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Reactions fetched",
                "data": {
                    "per_page": 50,
                    "current_page": 1,
                    "last_page": 1,
                    "reactions": [
                        {
                            "id": str(reaction.id),
                            "user": {
                                "name": user.full_name,
                                "username": user.username,
                                "avatar": user.get_avatar,
                            },
                            "rtype": reaction.rtype,
                        }
                    ],
                },
            },
        )

    async def test_create_reaction(self):
        post = self.post
        user = self.verified_user

        reaction_data = {"rtype": "LOVE"}

        # Test for invalid for_value
        response = await self.client.post(
            f"{self.reactions_url}invalid_for/{post.slug}/",
            reaction_data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "message": "Invalid 'focus' value",
                "code": ErrorCode.INVALID_VALUE,
            },
        )

        # Test for invalid slug
        response = await self.client.post(
            f"{self.reactions_url}POST/invalid_slug/",
            reaction_data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "message": "Post does not exist",
                "code": ErrorCode.NON_EXISTENT,
            },
        )

        # Test for valid values
        response = await self.client.post(
            f"{self.reactions_url}POST/{post.slug}/",
            reaction_data,
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Reaction created",
                "data": {
                    "id": mock.ANY,
                    "user": {
                        "name": user.full_name,
                        "username": user.username,
                        "avatar": user.get_avatar,
                    },
                    "rtype": reaction_data["rtype"],
                },
            },
        )

    async def test_delete_reaction(self):
        reaction = self.reaction

        # Test for invalid reaction id
        invalid_id = str(uuid.uuid4())
        response = await self.client.delete(
            f"{self.reactions_url}{invalid_id}/",
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "message": "Reaction does not exist",
                "code": ErrorCode.NON_EXISTENT,
            },
        )

        # Test for invalid owner
        response = await self.client.delete(
            f"{self.reactions_url}{reaction.id}/",
            content_type=self.content_type,
            **self.other_user_bearer,
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "message": "Not yours to delete",
                "code": ErrorCode.INVALID_OWNER,
            },
        )

        # Test for valid values
        response = await self.client.delete(
            f"{self.reactions_url}{reaction.id}/",
            content_type=self.content_type,
            **self.bearer,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Reaction deleted",
            },
        )

    async def test_retrieve_comments(self):
        comment = self.comment
        post = self.post
        user = self.verified_user

        # Test for invalid post slug
        response = await self.client.get(
            f"{self.posts_url}invalid_slug/comments/", content_type=self.content_type
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "status": "failure",
                "message": "Post does not exist",
                "code": ErrorCode.NON_EXISTENT,
            },
        )

        # Test for valid values
        response = await self.client.get(
            f"{self.posts_url}{post.slug}/comments/", content_type=self.content_type
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "success",
                "message": "Comments Fetched",
                "data": {
                    "per_page": 50,
                    "current_page": 1,
                    "last_page": 1,
                    "comments": [
                        {
                            "author": {
                                "name": user.full_name,
                                "username": user.username,
                                "avatar": user.get_avatar,
                            },
                            "slug": comment.slug,
                            "text": comment.text,
                            "replies_count": await comment.replies.acount(),
                        }
                    ],
                },
            },
        )
