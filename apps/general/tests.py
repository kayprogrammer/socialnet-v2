from django.test import TestCase
from django.test.client import AsyncClient


class TestGeneral(TestCase):
    sitedetail_url = "/api/v2/general/site-detail/"

    def setUp(self) -> None:
        self.client = AsyncClient()

    async def test_retrieve_sitedetail(self):
        response = await self.client.get(self.sitedetail_url)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Site Details fetched")
        keys = ["name", "email", "phone", "address", "fb", "tw", "wh", "ig"]
        self.assertTrue(all(item in result["data"] for item in keys))
