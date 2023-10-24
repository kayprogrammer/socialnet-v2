from django.db.models import Q, Prefetch
from apps.chat.models import Chat, Message
from apps.common.models import File


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
