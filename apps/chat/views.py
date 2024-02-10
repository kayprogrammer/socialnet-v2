from uuid import UUID
from django.db.models import Q
from apps.accounts.models import User
from apps.chat.consumers import send_message_deletion_in_socket
from apps.chat.models import Chat, Message
from apps.chat.utils import (
    create_file,
    get_chat_object,
    get_chats_queryset,
    get_message_object,
    update_group_chat_users,
    usernames_to_add_and_remove_validations,
)
from apps.common.error import ErrorCode
from apps.common.exceptions import RequestError
from apps.common.file_types import ALLOWED_FILE_TYPES
from apps.common.paginators import CustomPagination
from apps.common.responses import CustomResponse
from apps.common.schemas import ResponseSchema
from apps.common.utils import AuthUser, set_dict_attr
from ninja.router import Router
from .schemas import (
    ChatResponseSchema,
    ChatsResponseSchema,
    GroupChatCreateSchema,
    GroupChatInputResponseSchema,
    GroupChatInputSchema,
    MessageCreateResponseSchema,
    MessageCreateSchema,
    MessageUpdateSchema,
)
from asgiref.sync import sync_to_async

chats_router = Router(tags=["Chat"], auth=AuthUser())

paginator = CustomPagination()


@chats_router.get(
    "",
    summary="Retrieve User Chats",
    description="""
        This endpoint retrieves a paginated list of the current user chats
        Only chats with type "GROUP" have name, image and description.
    """,
    response=ChatsResponseSchema,
)
async def retrieve_user_chats(request, page: int = 1):
    user = await request.auth
    chats = await get_chats_queryset(user)
    paginator.page_size = 200
    paginated_data = await paginator.paginate_queryset(chats, page)
    return CustomResponse.success(message="Chats fetched", data=paginated_data)


@chats_router.post(
    "",
    summary="Send a message",
    description=f"""
        This endpoint sends a message.
        You must either send a text or a file or both.
        If there's no chat_id, then its a new chat and you must set username and leave chat_id
        If chat_id is available, then ignore username and set the correct chat_id
        The file_upload_data in the response is what is used for uploading the file to cloudinary from client
        ALLOWED FILE TYPES: {", ".join(ALLOWED_FILE_TYPES)}
    """,
    response={201: MessageCreateResponseSchema},
)
async def send_message(request, data: MessageCreateSchema):
    user = await request.auth
    chat_id = data.chat_id
    username = data.username

    # For sending
    chat = None
    if not chat_id:
        # Create a new chat dm with current user and recipient user
        recipient_user = await User.objects.aget_or_none(username=username)
        if not recipient_user:
            raise RequestError(
                err_code=ErrorCode.INVALID_ENTRY,
                err_msg="Invalid entry",
                status_code=422,
                data={"username": "No user with that username"},
            )

        chat = (
            await Chat.objects.filter(ctype="DM")
            .filter(
                Q(owner=user, users__id=recipient_user.id)
                | Q(owner=recipient_user, users__id=user.id)
            )
            .aget_or_none()
        )
        # Check if a chat already exists between both users
        if chat:
            raise RequestError(
                err_code=ErrorCode.INVALID_ENTRY,
                err_msg="Invalid entry",
                status_code=422,
                data={"username": "A chat already exist between you and the recipient"},
            )
        chat = await Chat.objects.acreate(owner=user, ctype="DM")
        await chat.users.aadd(recipient_user)
    else:
        # Get the chat with chat id and check if the current user is the owner or the recipient
        chat = await Chat.objects.filter(
            Q(owner=user) | Q(users__id=user.id)
        ).aget_or_none(id=chat_id)
        if not chat:
            raise RequestError(
                err_code=ErrorCode.NON_EXISTENT,
                err_msg="User has no chat with that ID",
                status_code=404,
            )

    # Create Message
    file = await create_file(data.file_type)
    file_upload_status = True if file else False
    message = await Message.objects.acreate(
        chat=chat, sender=user, text=data.text, file=file
    )
    message.file_upload_status = file_upload_status
    return CustomResponse.success(message="Message sent", data=message, status_code=201)


@chats_router.get(
    "/{chat_id}/",
    summary="Retrieve messages from a Chat",
    description="""
        This endpoint retrieves all messages in a chat.
    """,
    response=ChatResponseSchema,
)
async def retrieve_messages(request, chat_id: UUID, page: int = 1):
    user = await request.auth
    chat = await get_chat_object(user, chat_id)

    paginator.page_size = 400
    paginated_data = await paginator.paginate_queryset(chat.messages.all(), page)
    chat.lmessages = paginated_data["items"][:1]  # Latest message to be used in schema
    data = {"chat": chat, "messages": paginated_data, "users": chat.recipients}
    return CustomResponse.success(message="Messages fetched", data=data)


@chats_router.patch(
    "/{chat_id}/",
    summary="Update a Group Chat",
    description="""
        This endpoint updates a group chat.
    """,
    response=GroupChatInputResponseSchema,
)
async def update_group_chat(request, chat_id: UUID, data: GroupChatInputSchema):
    user = await request.auth
    chat = (
        await Chat.objects.select_related("image")
        .prefetch_related("users")
        .aget_or_none(owner=user, id=chat_id, ctype="GROUP")
    )
    if not chat:
        raise RequestError(
            err_code=ErrorCode.NON_EXISTENT,
            err_msg="User owns no group chat with that ID",
            status_code=404,
        )

    data = data.dict(exclude_none=True)

    # Handle Users Upload or Remove
    usernames_to_add = data.pop("usernames_to_add", None)
    usernames_to_remove = data.pop("usernames_to_remove", None)
    chat = await usernames_to_add_and_remove_validations(
        chat, usernames_to_add, usernames_to_remove
    )

    # Handle File Upload
    file_type = data.pop("file_type", None)
    file_upload_status = False
    if file_type:
        file_upload_status = True
        if chat.image:
            chat.image.resource_type = file_type
            await chat.image.asave()
        else:
            file = await create_file(file_type)
            data["image"] = file

    chat = set_dict_attr(chat, data)
    await chat.asave()
    chat.recipients = await sync_to_async(list)(chat.users.select_related("avatar"))
    chat.file_upload_status = file_upload_status
    return CustomResponse.success(message="Chat updated", data=chat)


@chats_router.delete(
    "/{chat_id}/",
    summary="Delete a Group Chat",
    description="""
        This endpoint deletes a group chat.
    """,
    response=ResponseSchema,
)
async def delete_group_chat(request, chat_id: UUID):
    user = await request.auth
    chat = await Chat.objects.aget_or_none(owner=user, id=chat_id, ctype="GROUP")
    if not chat:
        raise RequestError(
            err_code=ErrorCode.NON_EXISTENT,
            err_msg="User owns no group chat with that ID",
            status_code=404,
        )
    await chat.adelete()
    return CustomResponse.success(message="Group Chat Deleted")


@chats_router.put(
    "/messages/{message_id}/",
    summary="Update a message",
    description=f"""
        This endpoint updates a message.
        You must either send a text or a file or both.
        The file_upload_data in the response is what is used for uploading the file to cloudinary from client
        ALLOWED FILE TYPES: {", ".join(ALLOWED_FILE_TYPES)}
    """,
    response=MessageCreateResponseSchema,
)
async def update_message(request, message_id: UUID, data: MessageUpdateSchema):
    user = await request.auth
    message = await get_message_object(message_id, user)

    data = data.dict(exclude_none=True)
    # Handle File Upload
    file_upload_status = False
    file_type = data.pop("file_type", None)
    if file_type:
        file_upload_status = True
        if message.file:
            message.file.resource_type = file_type
            await message.file.asave()
        else:
            file = await create_file(file_type)
            data["file"] = file

    message = set_dict_attr(message, data)
    await message.asave()
    message.file_upload_status = file_upload_status
    return CustomResponse.success(message="Message updated", data=message)


@chats_router.delete(
    "/messages/{message_id}/",
    summary="Delete a message",
    description="""
        This endpoint deletes a message.
    """,
    response=ResponseSchema,
)
async def delete_message(request, message_id: UUID):
    user = await request.auth
    message = await get_message_object(message_id, user)
    chat = message.chat
    messages_count = await chat.messages.acount()

    # Send message deletion socket
    await send_message_deletion_in_socket(
        request.is_secure(), request.get_host(), chat.id, message.id
    )

    # Delete message and chat if its the last message in the dm being deleted
    if messages_count == 1 and chat.ctype == "DM":
        await chat.adelete()  # Message deletes if chat gets deleted (CASCADE)
    else:
        await message.adelete()
    return CustomResponse.success(message="Message deleted")


@chats_router.post(
    "/groups/group/",
    summary="Create a group chat",
    description="""
        This endpoint creates a group chat.
        The users_entry field should be a list of usernames you want to add to the group.
        Note: You cannot add more than 99 users in a group (1 owner + 99 other users = 100 users total)
    """,
    response={201: GroupChatInputResponseSchema},
)
async def create_group_chat(request, data: GroupChatCreateSchema):
    user = await request.auth
    data = data.dict(exclude_none=True)
    data.update({"owner": user, "ctype": "GROUP"})

    # Handle Users Upload
    usernames_to_add = data.pop("usernames_to_add")
    users_to_add = await sync_to_async(list)(
        User.objects.filter(username__in=usernames_to_add)
        .exclude(id=user.id)
        .select_related("avatar")
    )
    if len(users_to_add) < 1:
        raise RequestError(
            err_code=ErrorCode.INVALID_ENTRY,
            err_msg="Invalid Entry",
            data={"usernames_to_add": "Enter at least one valid username"},
            status_code=422,
        )

    # Handle File Upload
    file_type = data.pop("file_type", None)
    file_upload_status = False
    if file_type:
        file_upload_status = True
        file = await create_file(file_type)
        data["image"] = file

    # Create Chat
    chat = await Chat.objects.acreate(**data)
    chat.recipients = users_to_add
    await sync_to_async(update_group_chat_users)(chat, "add", users_to_add)
    chat.file_upload_status = file_upload_status
    return CustomResponse.success(message="Chat created", data=chat, status_code=201)
