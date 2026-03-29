"""Public Dishka helpers for FastAPI and Starlette web dependencies.

Purpose:
    Resolve request-scoped Dishka services through FastAPI `Depends` and the
    `request.state.dishka_container` set by `starlette-dishka` middleware.

Relationships:
    - Used by HTTP route modules and auth dependencies instead of the retired
      hybrid `skriptoteket.web.dishka_compat` decorator path.
    - Provides the explicit websocket-aware resolution path for future
      websocket endpoints via `resolve_from_websocket`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, TypeVar, cast

from fastapi import Depends, Request, WebSocket

T = TypeVar("T")


def from_dishka(dependency_type: type[T]) -> Any:
    """Create a FastAPI dependency that resolves a Dishka service from request state."""

    async def dependency(request: Request) -> T:
        return cast(T, await request.state.dishka_container.get(dependency_type))

    return Depends(dependency)


if TYPE_CHECKING:
    type FromDishka[T] = T
else:

    class FromDishka:
        """Annotated alias that keeps route signatures concise for Dishka-backed HTTP DI."""

        def __class_getitem__(cls, dependency_type: Any) -> Any:
            return Annotated[dependency_type, from_dishka(dependency_type)]


async def resolve_from_websocket(websocket: WebSocket, dependency_type: type[T]) -> T:
    """Resolve a Dishka service explicitly from websocket state."""

    return cast(T, await websocket.state.dishka_container.get(dependency_type))


__all__ = ["FromDishka", "from_dishka", "resolve_from_websocket"]
