from django.db.models import Q
from apps.accounts.models import User
from apps.chat.models import Chat, Message
from apps.chat.utils import create_file, get_chats_queryset
from apps.common.error import ErrorCode
from apps.common.exceptions import RequestError
from apps.common.file_types import ALLOWED_FILE_TYPES, ALLOWED_IMAGE_TYPES
from apps.common.paginators import CustomPagination
from apps.common.responses import CustomResponse
from apps.common.utils import AuthUser
from ninja.router import Router
from .schemas import (
    ChatsResponseSchema,
    MessageCreateResponseSchema,
    MessageCreateSchema,
)

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
async def get(request, page: int = 1):
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

        WEBSOCKET ENDPOINT: /api/v2/ws/chat/:id/ e.g (ws://127.0.0.1:8000/api/v2/ws/chat/b7e23862-a1d8-4e31-8c63-9829b09ea595/) 
        NOTE:
        * This endpoint requires authorization, so pass in the Authorization header with Bearer and its value.
        * Use chat_id as the ID for existing chat or user id if its the first message in a DM.
        * You cannot read realtime messages from a user_id that doesn't belong to the current user, but you can surely send messages
        * Only send message to the socket endpoint after the message has been created, and files has been uploaded.
        * Fields when sending message through the socket: e.g {{"status": "CREATED", "id": "fe4e0235-80fc-4c94-b15e-3da63226f8ab"}}
            * status - This must be either CREATED, UPDATED or DELETED (str type)
            * id - This is the ID of the message (uuid type)
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
