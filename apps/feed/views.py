from uuid import UUID
from django.db.models import Count
from ninja import Path
from apps.common.file_types import ALLOWED_IMAGE_TYPES
from apps.common.paginators import CustomPagination
from apps.feed.utils import (
    get_comment_object,
    get_post_object,
    get_reaction_focus_object,
    get_reactions_queryset,
    get_reply_object,
)
from apps.profiles.models import Notification
from apps.profiles.utils import send_notification_in_socket
from .models import Post, Comment, Reply, Reaction
from apps.common.models import File
from apps.common.error import ErrorCode
from apps.common.exceptions import RequestError
from apps.common.schemas import ErrorResponseSchema, ResponseSchema
from apps.common.responses import CustomResponse
from apps.common.utils import AuthUser, set_dict_attr
from ninja.router import Router
from .schemas import (
    CommentInputSchema,
    CommentResponseSchema,
    CommentWithRepliesResponseSchema,
    CommentsResponseSchema,
    PostInputResponseSchema,
    PostInputSchema,
    PostResponseSchema,
    PostsResponseSchema,
    ReactionInputSchema,
    ReactionResponseSchema,
    ReactionsResponseSchema,
    ReplyResponseSchema,
)

feed_router = Router(tags=["Feed"])

paginator = CustomPagination()


@feed_router.get(
    "/posts/",
    summary="Retrieve Latest Posts",
    description="This endpoint retrieves paginated responses of latest posts",
    response=PostsResponseSchema,
)
async def retrieve_posts(request, page: int = 1):
    posts = (
        Post.objects.select_related("author", "author__avatar", "image")
        .annotate(reactions_count=Count("reactions"), comments_count=Count("comments"))
        .order_by("-created_at")
    )
    paginated_data = await paginator.paginate_queryset(posts, page)
    return CustomResponse.success(message="Posts fetched", data=paginated_data)


@feed_router.post(
    "/posts/",
    summary="Create Post",
    description=f"""
        This endpoint creates a new post
        ALLOWED FILE TYPES: {", ".join(ALLOWED_IMAGE_TYPES)}
    """,
    response={201: PostInputResponseSchema},
    auth=AuthUser(),
)
async def create_post(request, data: PostInputSchema):
    data = data.dict()
    file_type = data.pop("file_type", None)
    image_upload_status = False
    if file_type:
        file = await File.objects.acreate(resource_type=file_type)
        data["image"] = file
        image_upload_status = True

    data["author"] = await request.auth
    post = await Post.objects.acreate(**data)
    post.image_upload_status = image_upload_status
    return CustomResponse.success(message="Post created", data=post, status_code=201)


@feed_router.get(
    "/posts/{slug}/",
    summary="Retrieve Single Post",
    description="This endpoint retrieves a single post",
    response={200: PostResponseSchema, 404: ErrorResponseSchema},
)
async def retrieve_post(request, slug: str):
    post = await get_post_object(slug, "detailed")
    return CustomResponse.success(message="Post Detail fetched", data=post)


@feed_router.put(
    "/posts/{slug}/",
    summary="Update a Post",
    description="This endpoint updates a post",
    response=PostInputResponseSchema,
    auth=AuthUser(),
)
async def update_post(request, slug: str, data: PostInputSchema):
    post = await get_post_object(slug, "detailed")
    if post.author != await request.auth:
        raise RequestError(
            err_code=ErrorCode.INVALID_OWNER,
            err_msg="This Post isn't yours",
        )

    data = data.dict()
    file_type = data.pop("file_type", None)
    image_upload_status = False
    if file_type:
        file = post.image
        if not file:
            file = await File.objects.acreate(resource_type=file_type)
        else:
            file.resource_type = file_type
            await file.asave()
        data["image_id"] = file.id
        image_upload_status = True

    post = set_dict_attr(post, data)
    post.image_upload_status = image_upload_status
    await post.asave()
    return CustomResponse.success(message="Post updated", data=post)


@feed_router.delete(
    "/posts/{slug}/",
    summary="Delete a Post",
    description="This endpoint deletes a post",
    response=ResponseSchema,
    auth=AuthUser(),
)
async def delete_post(request, slug: str):
    post = await get_post_object(slug)
    if post.author_id != (await request.auth).id:
        raise RequestError(
            err_code=ErrorCode.INVALID_OWNER,
            err_msg="This Post isn't yours",
        )
    await post.adelete()
    return CustomResponse.success(message="Post deleted")


focus_query = Path(
    ...,
    description="Specify the usage. Use any of the three: POST, COMMENT, REPLY",
)
slug_query = Path(..., description="Enter the slug of the post or comment or reply")


@feed_router.get(
    "/reactions/{focus}/{slug}/",
    summary="Retrieve Latest Reactions of a Post, Comment, or Reply",
    description="""
        This endpoint retrieves paginated responses of reactions of post, comment, reply.
    """,
    response=ReactionsResponseSchema,
)
async def retrieve_reactions(
    request,
    focus: str = focus_query,
    slug: str = slug_query,
    reaction_type: str = None,
    page: int = 1,
):
    reactions = await get_reactions_queryset(focus, slug, reaction_type)
    paginated_data = await paginator.paginate_queryset(reactions, page)
    return CustomResponse.success(message="Reactions fetched", data=paginated_data)


@feed_router.post(
    "/reactions/{focus}/{slug}/",
    summary="Create Reaction",
    description="""
        This endpoint creates a new reaction
        rtype should be any of these:
        
        - LIKE    - LOVE
        - HAHA    - WOW
        - SAD     - ANGRY
    """,
    response={201: ReactionResponseSchema},
    auth=AuthUser(),
)
async def create_reaction(
    request,
    data: ReactionInputSchema,
    focus: str = focus_query,
    slug: str = slug_query,
):
    user = await request.auth
    obj = await get_reaction_focus_object(focus, slug)

    data = data.dict()
    data["user"] = user
    rtype = data.pop("rtype").value
    obj_field = focus.lower()  # Focus object field (e.g post, comment, reply)
    data[obj_field] = obj

    reaction = await Reaction.objects.select_related(
        "user", "user__avatar"
    ).aget_or_none(**data)
    if reaction:
        reaction.rtype = rtype
        await reaction.asave()
    else:
        data["rtype"] = rtype
        reaction = await Reaction.objects.acreate(**data)

    # Create and Send Notification
    if obj.author_id != user.id:
        ndata = {obj_field: obj}
        notification, created = await Notification.objects.select_related(
            "sender",
            "sender__avatar",
            "post",
            "comment",
            "comment__post",
            "reply",
            "reply__comment",
            "reply__comment__post",
        ).aget_or_create(sender=user, ntype="REACTION", **ndata)
        if created:
            await notification.receivers.aadd(obj.author)

            # Send to websocket
            await send_notification_in_socket(
                request.is_secure(),
                request.get_host(),
                notification,
            )

    return CustomResponse.success(
        message="Reaction created", data=reaction, status_code=201
    )


@feed_router.delete(
    "/reactions/{id}/",
    summary="Remove Reaction",
    description="""
        This endpoint deletes a reaction.
    """,
    response=ResponseSchema,
    auth=AuthUser(),
)
async def remove_reaction(request, id: UUID):
    user = await request.auth
    reaction = await Reaction.objects.select_related(
        "post", "comment", "reply"
    ).aget_or_none(id=id)
    if not reaction:
        raise RequestError(
            err_code=ErrorCode.NON_EXISTENT,
            err_msg="Reaction does not exist",
            status_code=404,
        )
    if user.id != reaction.user_id:
        raise RequestError(
            err_code=ErrorCode.INVALID_OWNER,
            err_msg="Not yours to delete",
            status_code=401,
        )

    # Remove Reaction Notification
    targeted_obj = reaction.targeted_obj
    targeted_field = f"{targeted_obj.__class__.__name__.lower()}_id"  # (post_id, comment_id or reply_id)
    data = {
        "sender": user,
        "ntype": "REACTION",
        targeted_field: targeted_obj.id,
    }

    notification = await Notification.objects.aget_or_none(**data)
    if notification:
        # Send to websocket and delete notification
        await send_notification_in_socket(
            request.is_secure(), request.get_host(), notification, status="DELETED"
        )
        await notification.adelete()

    await reaction.adelete()
    return CustomResponse.success(message="Reaction deleted")


# COMMENTS


@feed_router.get(
    "/posts/{slug}/comments/",
    summary="Retrieve Post Comments",
    description="""
        This endpoint retrieves comments of a particular post.
    """,
    response=CommentsResponseSchema,
)
async def retrieve_comments(request, slug: str, page: int = 1):
    post = await get_post_object(slug)
    comments = (
        Comment.objects.filter(post_id=post.id)
        .select_related("author", "author__avatar")
        .annotate(replies_count=Count("replies"), reactions_count=Count("reactions"))
    )
    paginated_data = await paginator.paginate_queryset(comments, page)
    return CustomResponse.success(message="Comments Fetched", data=paginated_data)


@feed_router.post(
    "/posts/{slug}/comments/",
    summary="Create Comment",
    description="""
        This endpoint creates a comment for a particular post.
    """,
    response={201: CommentResponseSchema},
    auth=AuthUser(),
)
async def create_comment(request, slug: str, data: CommentInputSchema):
    user = await request.auth
    post = await get_post_object(slug)
    comment = await Comment.objects.acreate(post=post, author=user, text=data.text)

    # Create and Send Notification
    if user.id != post.author_id:
        notification = await Notification.objects.acreate(
            sender=user, ntype="COMMENT", comment=comment
        )
        await notification.receivers.aadd(post.author_id)

        # Send to websocket
        await send_notification_in_socket(
            request.is_secure(),
            request.get_host(),
            notification,
        )

    return CustomResponse.success(
        message="Comment Created", data=comment, status_code=201
    )


@feed_router.get(
    "/comments/{slug}/",
    summary="Retrieve Comment with replies",
    description="""
        This endpoint retrieves a comment with replies.
    """,
    response=CommentWithRepliesResponseSchema,
)
async def retrieve_comment_with_replies(request, slug: str, page: int = 1):
    comment = await get_comment_object(slug)
    replies = (
        Reply.objects.filter(comment_id=comment.id)
        .annotate(reactions_count=Count("reactions"))
        .select_related("author", "author__avatar")
    )
    paginated_data = await paginator.paginate_queryset(replies, page)
    data = {"comment": comment, "replies": paginated_data}
    return CustomResponse.success(message="Comment and Replies Fetched", data=data)


@feed_router.post(
    "/comments/{slug}/",
    summary="Create Reply",
    description="""
        This endpoint creates a reply for a comment.
    """,
    response={201: ReplyResponseSchema},
    auth=AuthUser(),
)
async def create_reply(request, slug: str, data: CommentInputSchema):
    user = await request.auth
    comment = await get_comment_object(slug)
    reply = await Reply.objects.acreate(author=user, comment=comment, text=data.text)

    # Create and Send Notification
    if user.id != comment.author_id:
        notification = await Notification.objects.acreate(
            sender=user, ntype="REPLY", reply=reply
        )
        await notification.receivers.aadd(comment.author)

        # Send to websocket
        await send_notification_in_socket(
            request.is_secure(),
            request.get_host(),
            notification,
        )
    return CustomResponse.success(message="Reply Created", data=reply, status_code=201)


@feed_router.put(
    "/comments/{slug}/",
    summary="Update Comment",
    description="""
        This endpoint updates a particular comment.
    """,
    response=CommentResponseSchema,
    auth=AuthUser(),
)
async def update_comment(request, slug: str, data: CommentInputSchema):
    user = await request.auth
    comment = await get_comment_object(slug)
    if comment.author_id != user.id:
        raise RequestError(
            err_code=ErrorCode.INVALID_OWNER,
            err_msg="Not yours to edit",
            status_code=401,
        )
    comment.text = data.text
    await comment.asave()
    return CustomResponse.success(message="Comment Updated", data=comment)


@feed_router.delete(
    "/comments/{slug}/",
    summary="Delete Comment",
    description="""
        This endpoint deletes a comment.
    """,
    response=ResponseSchema,
    auth=AuthUser(),
)
async def delete_comment(request, slug: str):
    user = await request.auth
    comment = await get_comment_object(slug)
    if user.id != comment.author_id:
        raise RequestError(
            err_code=ErrorCode.INVALID_OWNER,
            err_msg="Not yours to delete",
            status_code=401,
        )

    # # Remove Comment Notification
    notification = await Notification.objects.aget_or_none(
        sender=user, ntype="COMMENT", comment_id=comment.id
    )
    if notification:
        # Send to websocket and delete notification
        await send_notification_in_socket(
            request.is_secure(), request.get_host(), notification, status="DELETED"
        )
        await notification.adelete()

    await comment.adelete()
    return CustomResponse.success(message="Comment Deleted")


@feed_router.get(
    "/replies/{slug}/",
    summary="Retrieve Reply",
    description="""
        This endpoint retrieves a reply.
    """,
    response=ReplyResponseSchema,
)
async def retrieve_reply(request, slug: str):
    reply = await get_reply_object(slug)
    return CustomResponse.success(message="Reply Fetched", data=reply)


@feed_router.put(
    "/replies/{slug}/",
    summary="Update Reply",
    description="""
        This endpoint updates a particular reply.
    """,
    response=ReplyResponseSchema,
    auth=AuthUser(),
)
async def update_reply(request, slug: str, data: CommentInputSchema):
    reply = await get_reply_object(slug)
    if reply.author_id != (await request.auth).id:
        raise RequestError(
            err_code=ErrorCode.INVALID_OWNER,
            err_msg="Not yours to edit",
            status_code=401,
        )
    reply.text = data.text
    await reply.asave()
    return CustomResponse.success(message="Reply Updated", data=reply)


@feed_router.delete(
    "/replies/{slug}/",
    summary="Delete reply",
    description="""
        This endpoint deletes a reply.
    """,
    response=ResponseSchema,
    auth=AuthUser(),
)
async def delete_reply(request, slug: str):
    user = await request.auth
    reply = await get_reply_object(slug)
    if user.id != reply.author_id:
        raise RequestError(
            err_code=ErrorCode.INVALID_OWNER,
            err_msg="Not yours to delete",
            status_code=401,
        )

    # Remove Reply Notification
    notification = await Notification.objects.aget_or_none(
        sender=user, ntype="REPLY", reply_id=reply.id
    )
    if notification:
        # Send to websocket and delete notification
        await send_notification_in_socket(
            request.is_secure(), request.get_host(), notification, status="DELETED"
        )
        await notification.adelete()

    await reply.adelete()
    return CustomResponse.success(message="Reply Deleted")
