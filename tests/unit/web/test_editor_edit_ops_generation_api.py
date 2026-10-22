"""Editor edit-ops generation route tests.

Purpose:
    Verify edit-op generation access (signed-in contributor and above),
    eval-mode authorization and door-limit refusal at the FastAPI boundary.

Relationships:
    - Fixtures live in `tests.fixtures.editor_edit_ops_api_app`.
    - Preview and apply live in `test_editor_edit_ops_preview_apply_api.py`.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.llm_door import AiDailyLimit, ai_limit_note
from skriptoteket.protocols.llm import (
    EditOpsResult,
    PromptEvalMeta,
)
from tests.fixtures.profile_app_continuation_support import (
    ClockStub,
    ProfileRepositoryStub,
    UserRepositoryStub,
    seed_huleedu_projection,
    signed_huleedu_headers,
)
from tests.unit.web.editor_edit_ops_test_support import virtual_files

pytest_plugins = ("tests.fixtures.editor_edit_ops_api_app",)


@pytest.mark.asyncio
async def test_edit_ops_eval_headers_require_admin_role_metadata(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.CONTRIBUTOR, now=now)
    headers = signed_huleedu_headers(private_key=private_key, clock=clock)
    headers["X-Skriptoteket-Eval"] = "1"

    response = await client.post(
        "/api/v1/editor/edit-ops",
        headers=headers,
        json={
            "tool_id": str(uuid4()),
            "message": "Patch this",
            "active_file": "tool.py",
            "virtual_files": virtual_files("print('hi')\n"),
        },
    )

    assert response.status_code == 403
    details = response.json()["error"]["details"]
    assert set(details["required_roles"]) == {"admin", "superuser"}
    assert details["actual_role"] == "contributor"
    handler.handle.assert_not_awaited()


@pytest.mark.asyncio
async def test_edit_ops_ai_gate_rejects_a_user_below_contributor(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.USER, now=now)

    response = await client.post(
        "/api/v1/editor/edit-ops",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        json={
            "tool_id": str(uuid4()),
            "message": "Patch this",
            "active_file": "tool.py",
            "virtual_files": virtual_files("print('hi')\n"),
        },
    )

    assert response.status_code == 403
    details = response.json()["error"]["details"]
    assert details["required_role"] == "contributor"
    assert details["actual_role"] == "user"
    handler.handle.assert_not_awaited()


@pytest.mark.asyncio
async def test_edit_ops_ai_gate_serves_a_signed_in_contributor(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.CONTRIBUTOR, now=now)
    handler.handle.return_value = EditOpsResult(
        enabled=True,
        assistant_message="ok",
        ops=[],
        base_fingerprints={},
    )

    response = await client.post(
        "/api/v1/editor/edit-ops",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        json={
            "tool_id": str(uuid4()),
            "message": "Patch this",
            "active_file": "tool.py",
            "virtual_files": virtual_files("print('hi')\n"),
        },
    )

    assert response.status_code == 200
    assert response.json()["enabled"] is True
    handler.handle.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [Role.ADMIN, Role.SUPERUSER])
async def test_edit_ops_ai_gate_admits_admin_roles(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
    role: Role,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=role, now=now)
    handler.handle.return_value = EditOpsResult(
        enabled=True,
        assistant_message="ok",
        ops=[],
        base_fingerprints={},
    )

    response = await client.post(
        "/api/v1/editor/edit-ops",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        json={
            "tool_id": str(uuid4()),
            "message": "Patch this",
            "active_file": "tool.py",
            "virtual_files": virtual_files("print('hi')\n"),
        },
    )

    assert response.status_code == 200
    assert response.json()["enabled"] is True
    handler.handle.assert_awaited_once()


@pytest.mark.asyncio
async def test_edit_ops_eval_headers_admit_an_admin_outside_production(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.ADMIN, now=now)
    handler.handle.return_value = EditOpsResult(
        enabled=True,
        assistant_message="ok",
        ops=[],
        base_fingerprints={},
        eval_meta=PromptEvalMeta(
            template_id="edit_ops_v1",
            outcome="ok",
            system_prompt_chars=10,
            prefix_chars=3,
            suffix_chars=4,
            instruction_chars=11,
            selection_chars=5,
        ),
    )
    headers = signed_huleedu_headers(private_key=private_key, clock=clock)
    headers["X-Skriptoteket-Eval"] = "1"

    response = await client.post(
        "/api/v1/editor/edit-ops",
        headers=headers,
        json={
            "tool_id": str(uuid4()),
            "message": "Patch this",
            "active_file": "tool.py",
            "virtual_files": virtual_files("print('hi')\n"),
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Skriptoteket-Eval-Template-Id"] == "edit_ops_v1"
    assert response.headers["X-Skriptoteket-Eval-Outcome"] == "ok"
    assert response.headers["X-Skriptoteket-Eval-Instruction-Chars"] == "11"
    assert response.headers["X-Skriptoteket-Eval-Selection-Chars"] == "5"
    handler.handle.assert_awaited_once()


@pytest.mark.asyncio
async def test_edit_ops_door_limit_refusal_is_a_429_with_the_limit_note(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.ADMIN, now=now)
    handler.handle.side_effect = DomainError(
        code=ErrorCode.AI_DAILY_LIMIT_REACHED,
        message=ai_limit_note(AiDailyLimit.POOL),
        details={"limit": AiDailyLimit.POOL.value},
    )

    response = await client.post(
        "/api/v1/editor/edit-ops",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        json={
            "tool_id": str(uuid4()),
            "message": "Patch this",
            "active_file": "tool.py",
            "virtual_files": virtual_files("print('hi')\n"),
        },
    )

    assert response.status_code == 429
    error = response.json()["error"]
    assert error["code"] == "AI_DAILY_LIMIT_REACHED"
    assert error["message"] == "Appens AI-hjälp har nått dagens gräns. Försök igen i morgon."
    assert error["details"] == {"limit": "pool"}
