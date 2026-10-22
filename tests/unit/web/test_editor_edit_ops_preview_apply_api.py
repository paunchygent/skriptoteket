"""Editor edit-ops preview and apply route tests.

Purpose:
    Verify edit-op preview and apply mapping at the FastAPI boundary.

Relationships:
    - Fixtures live in `tests.fixtures.editor_edit_ops_api_app`.
    - Generation access and eval mode live in
      `test_editor_edit_ops_generation_api.py`.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.llm import (
    EditOpsPreviewMeta,
    EditOpsPreviewResult,
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
async def test_edit_ops_preview_maps_web_ops_to_domain_command(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    preview_handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.CONTRIBUTOR, now=now)

    tool_id = uuid4()
    preview_handler.handle.return_value = EditOpsPreviewResult(
        ok=True,
        after_virtual_files=virtual_files("print('preview')\n"),
        errors=[],
        error_details=[],
        meta=EditOpsPreviewMeta(
            base_hash="sha256:base",
            patch_id="sha256:patch",
            requires_confirmation=False,
            fuzz_level_used=0,
            max_offset=0,
            normalizations_applied=[],
            applied_cleanly=True,
        ),
    )

    response = await client.post(
        "/api/v1/editor/edit-ops/preview",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        json={
            "tool_id": str(tool_id),
            "active_file": "tool.py",
            "virtual_files": virtual_files("print('hi')\n"),
            "ops": [
                {
                    "op": "patch",
                    "target_file": "tool.py",
                    "patch_lines": [
                        "@@ -1 +1 @@",
                        "-print('hi')",
                        "+print('preview')",
                    ],
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True

    called = preview_handler.handle.call_args.kwargs["command"]
    assert called.ops[0].op == "patch"
    assert called.ops[0].target_file == "tool.py"


@pytest.mark.asyncio
async def test_edit_ops_apply_maps_web_ops_and_includes_gating_tokens(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    apply_handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.CONTRIBUTOR, now=now)

    tool_id = uuid4()
    apply_handler.handle.return_value = EditOpsPreviewResult(
        ok=True,
        after_virtual_files=virtual_files("print('applied')\n"),
        errors=[],
        error_details=[],
        meta=EditOpsPreviewMeta(
            base_hash="sha256:base",
            patch_id="sha256:patch",
            requires_confirmation=False,
            fuzz_level_used=0,
            max_offset=0,
            normalizations_applied=[],
            applied_cleanly=True,
        ),
    )

    response = await client.post(
        "/api/v1/editor/edit-ops/apply",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        json={
            "tool_id": str(tool_id),
            "active_file": "tool.py",
            "virtual_files": virtual_files("print('hi')\n"),
            "ops": [
                {
                    "op": "patch",
                    "target_file": "tool.py",
                    "patch_lines": [
                        "@@ -1 +1 @@",
                        "-print('hi')",
                        "+print('applied')",
                    ],
                }
            ],
            "base_hash": "sha256:base",
            "patch_id": "sha256:patch",
        },
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True

    called = apply_handler.handle.call_args.kwargs["command"]
    assert called.base_hash == "sha256:base"
    assert called.patch_id == "sha256:patch"
    assert called.ops[0].op == "patch"
