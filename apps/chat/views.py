from apps.chat.utils import get_chats_queryset
from apps.common.file_types import ALLOWED_IMAGE_TYPES
from apps.common.paginators import CustomPagination
from apps.common.responses import CustomResponse
from apps.common.utils import AuthUser
from ninja.router import Router
from .schemas import ChatsResponseSchema

chats_router = Router(tags=["Chat"])

paginator = CustomPagination()


@chats_router.get(
    "",
    summary="Retrieve User Chats",
    description="""
        This endpoint retrieves a paginated list of the current user chats
        Only chats with type "GROUP" have name, image and description.
    """,
    response=ChatsResponseSchema,
    auth=AuthUser(),
)
async def get(request, page: int = 1):
    user = await request.auth
    chats = await get_chats_queryset(user)
    paginator.page_size = 200
    paginated_data = await paginator.paginate_queryset(chats, page)
    return CustomResponse.success(message="Chats fetched", data=paginated_data)
