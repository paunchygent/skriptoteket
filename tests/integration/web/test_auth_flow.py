from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.integration
async def test_login_page_loads(client: AsyncClient) -> None:
    response = await client.get("/login")
    assert response.status_code == 200
    assert "Logga in" in response.text or "Login" in response.text
