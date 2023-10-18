from apps.common.error import ErrorCode
from apps.common.exceptions import RequestError
from apps.feed.models import Comment, Post, Reply

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
