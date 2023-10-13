from typing import Any, List
from ninja.pagination import PaginationBase
from ninja import Schema
from asgiref.sync import sync_to_async


class CustomPagination(PaginationBase):
    page_size = 10  # Set the default page size here

    class Output(Schema):
        items: List[Any]  # `items` is a default attribute
        total: int
        per_page: int

    async def paginate_queryset(self, queryset, current_page):
        page_size = self.page_size
        async_queryset = await sync_to_async(list)(queryset)
        print(async_queryset)
        return {
            "items": async_queryset[current_page : current_page + page_size],
            "total": await queryset.acount(),
            "per_page": page_size,
        }
