from django.db.models import Count
from asgiref.sync import sync_to_async
from apps.common.file_types import ALLOWED_IMAGE_TYPES
from apps.common.paginators import CustomPagination
from apps.profiles.models import Notification
from apps.profiles.utils import send_notification_in_socket
from .models import Post, Comment, Reply, Reaction, REACTION_CHOICES
from apps.common.models import File
from apps.common.error import ErrorCode
from apps.common.exceptions import RequestError
from apps.common.schemas import ResponseSchema
from apps.common.responses import CustomResponse
from apps.common.utils import AuthUser
from ninja.router import Router
from .schemas import PostInputResponseSchema, PostInputSchema, PostsResponseSchema

feed_router = Router(tags=["Feed"])

paginator = CustomPagination()


@feed_router.get(
    "/posts/",
    summary="Retrieve Latest Posts",
    description="This endpoint retrieves paginated responses of latest posts",
    response=PostsResponseSchema,
)
async def retrieve_posts(request, page: int = 1):
    paginator.page_size = 50
    posts = (
        Post.objects.select_related("author", "image")
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
