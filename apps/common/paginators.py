from typing import Any, List
from ninja.pagination import PaginationBase
from ninja import Schema
from asgiref.sync import sync_to_async
from apps.common.error import ErrorCode

from apps.common.exceptions import RequestError
import math


class CustomPagination(PaginationBase):
    page_size = 50  # Set the default page size here

    class Output(Schema):
        items: List[Any]  # `items` is a default attribute
        total: int
        per_page: int

    async def paginate_queryset(self, queryset, current_page):
        if current_page < 1:
            raise RequestError(
                err_code=ErrorCode.INVALID_PAGE, err_msg="Invalid Page", status_code=404
            )
        page_size = self.page_size
        async_queryset = await sync_to_async(list)(queryset)
        queryset_count = await queryset.acount()
        items = async_queryset[
            (current_page - 1) * page_size : current_page * page_size
        ]
        if queryset_count > 0 and not items:
            raise RequestError(
                err_code=ErrorCode.INVALID_PAGE,
                err_msg="Page number is out of range",
                status_code=400,
            )

        last_page = math.ceil(queryset_count / page_size)
        last_page = 1 if last_page == 0 else last_page
        return {
            "items": items,
            "per_page": page_size,
            "current_page": current_page,
            "last_page": last_page,
        }
