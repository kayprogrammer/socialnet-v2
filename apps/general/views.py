from ninja import Router

from .schemas import (
    SiteDetailResponseSchema,
)
from .models import SiteDetail

general_router = Router(tags=["General"])


@general_router.get(
    "/site-detail/",
    response=SiteDetailResponseSchema,
    summary="Retrieve site details",
    description="This endpoint retrieves few details of the site/application",
)
async def retrieve_site_details(request):
    sitedetail, created = await SiteDetail.objects.aget_or_create()
    return {"message": "Site Details fetched", "data": sitedetail}
