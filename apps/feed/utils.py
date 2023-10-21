from typing import Literal
from django.db.models import Count
from apps.common.error import ErrorCode
from apps.common.exceptions import RequestError
from apps.feed.models import Comment, Post, Reaction, Reply

reaction_focus = {"POST": Post, "COMMENT": Comment, "REPLY": Reply}


async def validate_reaction_focus(focus):
    if not focus in list(reaction_focus.keys()):
        raise RequestError(
            err_code=ErrorCode.INVALID_VALUE,
            err_msg="Invalid 'focus' value",
            status_code=404,
        )
    return reaction_focus[focus]


async def get_reaction_focus_object(focus, slug):
    focus_model = await validate_reaction_focus(focus)
    related = ["author"]  # Related object to preload
    if focus_model == Comment:
        related.append("post")  # Also preload post object for comment
    obj = await focus_model.objects.select_related(*related).aget_or_none(slug=slug)
    if not obj:
        raise RequestError(
            err_code=ErrorCode.NON_EXISTENT,
            err_msg=f"{focus.capitalize()} does not exist",
            status_code=404,
        )
    return obj


async def get_post_object(slug, object_type: Literal["simple", "detailed"] = "simple"):
    # object_type simple fetches the post object without prefetching related objects because they aren't needed
    # detailed fetches the post object with the related objects because they are needed

    post = Post.objects
    if object_type == "detailed":
        post = post.select_related("author", "author__avatar", "image").annotate(
            reactions_count=Count("reactions"), comments_count=Count("comments")
        )
    post = await post.aget_or_none(slug=slug)
    if not post:
        raise RequestError(
            err_code=ErrorCode.NON_EXISTENT,
            err_msg="Post does not exist",
            status_code=404,
        )
    return post


async def get_reactions_queryset(focus, slug, rtype=None):
    focus_obj = await get_reaction_focus_object(focus, slug)
    focus_obj_field = f"{focus.lower()}_id"  # Field to filter reactions by (e.g post_id, comment_id, reply_id)
    filter = {focus_obj_field: focus_obj.id}
    if rtype:
        filter["rtype"] = rtype  # Filter by reaction type if the query param is present
    reactions = Reaction.objects.filter(**filter).select_related("user", "user__avatar")
    return reactions


async def get_comment_object(slug):
    comment = (
        await Comment.objects.select_related("author", "author__avatar", "post")
        .annotate(replies_count=Count("replies"))
        .aget_or_none(slug=slug)
    )
    if not comment:
        raise RequestError(
            err_code=ErrorCode.NON_EXISTENT,
            err_msg="Comment does not exist",
            status_code=404,
        )
    return comment


async def get_reply_object(slug):
    reply = await Reply.objects.select_related("author", "author__avatar").aget_or_none(
        slug=slug
    )
    if not reply:
        raise RequestError(
            err_code=ErrorCode.NON_EXISTENT,
            err_msg="Reply does not exist",
            status_code=404,
        )
    return reply
