from django.db.models import Q, Prefetch
from apps.chat.models import Chat, Message


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
