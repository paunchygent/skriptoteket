from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

from starlette.requests import Request
from starlette.responses import Response

from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.identity.models import AuthProvider, Role, Session, User
from skriptoteket.domain.scripting.models import ToolVersion, VersionState, compute_content_hash

type _AsyncHandler = Callable[..., Awaitable[Response]]


@runtime_checkable
class _DishkaWrappedHandler(Protocol):
    __dishka_orig_func__: _AsyncHandler

    def __call__(self, *args: object, **kwargs: object) -> Awaitable[Response]: ...


def _original(fn: _AsyncHandler | _DishkaWrappedHandler) -> _AsyncHandler:
    return fn.__dishka_orig_func__ if isinstance(fn, _DishkaWrappedHandler) else fn


def _request(*, path: str, headers: dict[str, str] | None = None) -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": raw_headers,
        "query_string": b"",
    }
    return Request(scope)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user(*, role: Role) -> User:
    now = _now()
    return User(
        id=uuid.uuid4(),
        email=f"{role.value}@example.com",
        role=role,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )


def _session(*, user_id: uuid.UUID) -> Session:
    now = _now()
    return Session(
        id=uuid.uuid4(),
        user_id=user_id,
        csrf_token="csrf",
        created_at=now,
        expires_at=now + timedelta(days=1),
    )


def _tool(*, title: str = "Tool") -> Tool:
    now = _now()
    return Tool(
        id=uuid.uuid4(),
        owner_user_id=uuid.uuid4(),
        slug="tool",
        title=title,
        summary="Summary",
        is_published=False,
        active_version_id=None,
        created_at=now,
        updated_at=now,
    )


def _version(
    *,
    tool_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    state: VersionState,
    version_number: int = 1,
    source_code: str = (
        "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>ok</p>'\n"
    ),
) -> ToolVersion:
    now = _now()
    entrypoint = "run_tool"
    return ToolVersion(
        id=uuid.uuid4(),
        tool_id=tool_id,
        version_number=version_number,
        state=state,
        source_code=source_code,
        entrypoint=entrypoint,
        content_hash=compute_content_hash(entrypoint=entrypoint, source_code=source_code),
        derived_from_version_id=None,
        created_by_user_id=created_by_user_id,
        created_at=now,
        submitted_for_review_by_user_id=None,
        submitted_for_review_at=None,
        reviewed_by_user_id=None,
        reviewed_at=None,
        published_by_user_id=None,
        published_at=None,
        change_summary=None,
        review_note=None,
    )
