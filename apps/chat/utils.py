from django.db.models import Q, Prefetch
from apps.accounts.models import User
from apps.chat.models import Chat, Message
from apps.common.error import ErrorCode
from apps.common.exceptions import RequestError
from apps.common.models import File
from asgiref.sync import sync_to_async


# Create file object
async def create_file(file_type=None):
    file = None
    if file_type:
        file = await File.objects.acreate(resource_type=file_type)
    return file


# Update group chat users m2m
def update_group_chat_users(instance, action, data):
    if len(data) > 0:
        if action == "add":
            instance.users.add(*data)
        elif action == "remove":
            instance.users.remove(*data)
        else:
            raise ValueError("Invalid Action")


async def get_chats_queryset(user):
    chats = (
        Chat.objects.filter(Q(owner=user) | Q(users__id=user.id))
        .select_related("owner", "owner__avatar", "image")
        .prefetch_related(
            Prefetch(
                "messages",
                queryset=Message.objects.select_related(
                    "sender", "sender__avatar", "file"
                ).order_by("-created_at"),
                to_attr="lmessages",
            )
        )
        .distinct()
    )
    return chats


async def get_chat_object(user, chat_id):
    chat = (
        await Chat.objects.filter(Q(owner=user) | Q(users__id=user.id))
        .select_related("owner", "owner__avatar", "image")
        .prefetch_related(
            Prefetch(
                "messages",
                queryset=Message.objects.select_related(
                    "sender", "sender__avatar", "file"
                ).order_by("-created_at"),
            ),
            Prefetch(
                "users",
                queryset=User.objects.select_related("avatar"),
                to_attr="recipients",
            ),
        )
        .aget_or_none(id=chat_id)
    )
    if not chat:
        raise RequestError(
            err_code=ErrorCode.NON_EXISTENT,
            err_msg="User has no chat with that ID",
            status_code=404,
        )
    return chat


async def get_message_object(message_id, user):
    message = await Message.objects.select_related(
        "sender", "chat", "sender__avatar", "file"
    ).aget_or_none(id=message_id, sender=user)
    if not message:
        raise RequestError(
            err_code=ErrorCode.NON_EXISTENT,
            err_msg="User has no message with that ID",
            status_code=404,
        )
    return message


async def usernames_to_add_and_remove_validations(
    chat, usernames_to_add=None, usernames_to_remove=None
):
    original_existing_user_ids = await sync_to_async(list)(
        chat.users.values_list("id", flat=True)
    )
    expected_user_total = len(original_existing_user_ids)
    users_to_add = []
    if usernames_to_add:
        users_to_add = await sync_to_async(list)(
            User.objects.filter(username__in=usernames_to_add).exclude(
                Q(id__in=original_existing_user_ids) | Q(id=chat.owner_id)
            )
        )
        expected_user_total += len(users_to_add)
    users_to_remove = []
    if usernames_to_remove:
        if not original_existing_user_ids:
            raise RequestError(
                err_code=ErrorCode.INVALID_ENTRY,
                err_msg="Invalid Entry",
                status_code=422,
                data={"usernames_to_remove": "No users to remove"},
            )
        users_to_remove = await sync_to_async(list)(
            User.objects.filter(
                username__in=usernames_to_remove, id__in=original_existing_user_ids
            ).exclude(id=chat.owner_id)
        )
        expected_user_total -= len(users_to_remove)

    if expected_user_total > 7:
        raise RequestError(
            err_code=ErrorCode.INVALID_ENTRY,
            err_msg="Invalid Entry",
            status_code=422,
            data={"usernames_to_add": "99 users limit reached"},
        )

    if users_to_add:
        await sync_to_async(update_group_chat_users)(chat, "add", users_to_add)
    if users_to_remove:
        await sync_to_async(update_group_chat_users)(chat, "remove", users_to_remove)
    return chat
