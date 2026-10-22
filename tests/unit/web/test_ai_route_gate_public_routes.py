"""Public-route AI guard for the guest exam workspace.

Purpose:
    Prove that no public or guest route can start an LLM call: every route
    under `/api/v1/public/` stays free of LLM client reach, every
    LLM-reaching route anywhere belongs to a signed-in caller through the
    sign-in dependency chain, and the guest exam-workspace surface stays
    public, LLM-free and free of `require_app_*` auth dependencies. A later
    edit that wires an AI dependency into a guest route fails this module.

Relationships:
    - Extends the sign-in guard in `test_ai_route_gate_coverage.py` without
      changing it; discovery and policy live in `ai_route_gate_discovery.py`
      and `ai_route_gate_policy.py`.
    - Reuses `create_app` so the asserted routes are the real production wiring.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute

from skriptoteket.protocols.llm import InlineCompletionHandlerProtocol
from skriptoteket.web.api.v1.public_apps import EXAM_CONVERTER_PUBLIC_API_NAMESPACE
from skriptoteket.web.app import create_app
from skriptoteket.web.dishka_dependencies import FromDishka
from tests.unit.web.ai_route_gate_discovery import (
    build_di_graph,
    closure,
    dependency_call_names,
    dependency_types,
    describe_routes,
    types_reaching_llm,
)
from tests.unit.web.ai_route_gate_policy import AI_ROLE_GATE

pytestmark = pytest.mark.unit

PUBLIC_API_PREFIX = "/api/v1/public/"
GUEST_WORKSPACE_PREFIX = f"{EXAM_CONVERTER_PUBLIC_API_NAMESPACE}/workspace"

# The pinned guest exam-workspace surface (G1): exact paths under the public
# exam-converter namespace. Presence is asserted so a removed route fails here;
# LLM-freeness and auth-freeness are asserted for the whole guest set so a
# later AI wiring fails here too.
REQUIRED_GUEST_WORKSPACE_PATHS: frozenset[str] = frozenset(
    {
        f"{GUEST_WORKSPACE_PREFIX}/blank",
        f"{GUEST_WORKSPACE_PREFIX}/parents",
        f"{GUEST_WORKSPACE_PREFIX}/change-type",
        f"{GUEST_WORKSPACE_PREFIX}/answer-misspellings",
        f"{GUEST_WORKSPACE_PREFIX}/courses",
        f"{GUEST_WORKSPACE_PREFIX}/exports/{{target}}",
        f"{GUEST_WORKSPACE_PREFIX}/export-checklist",
    }
)


@pytest.fixture(scope="module")
def di_graph() -> tuple[dict[type, set[type]], set[type]]:
    return build_di_graph()


@pytest.fixture(scope="module")
def reached_llm(di_graph: tuple[dict[type, set[type]], set[type]]) -> set[type]:
    # Reused as-is because it already covers every LLM client class:
    # `llm_client_classes()` enumerates every class under
    # `skriptoteket.infrastructure.llm` that implements a paid protocol, and
    # every class in that package that starts an LLM call (takes an
    # `httpx.AsyncClient`) implements one. The remaining classes there are
    # support services (failover routing, token counting, capture storage,
    # payload types) that start no LLM call.
    edges, inline_roots = di_graph
    return types_reaching_llm(edges, inline_roots)


@pytest.fixture(scope="module")
def app() -> FastAPI:
    return create_app()


def app_auth_dependency_names() -> frozenset[str]:
    """Every `require_app_*` gate defined in the web auth package."""
    import skriptoteket.web.auth as auth_package

    found: set[str] = set()
    modules = pkgutil.walk_packages(auth_package.__path__, auth_package.__name__ + ".")
    for module_info in modules:
        module = importlib.import_module(module_info.name)
        for name, candidate in inspect.getmembers(module, inspect.isfunction):
            if candidate.__module__ != module.__name__:
                continue
            if name.startswith("require_app_"):
                found.add(name)
    return frozenset(found)


def route_closure_reaches_llm(
    route: APIRoute,
    reached: set[type],
    edges: dict[type, set[type]],
) -> bool:
    """True when a dependency type or its DI closure contains an LLM-reaching type."""
    return any(
        closure(dependency_type, edges) & reached
        for dependency_type in dependency_types(route.dependant)
    )


def public_routes_reaching_llm(
    app: FastAPI,
    reached: set[type],
    edges: dict[type, set[type]],
) -> set[tuple[str, str]]:
    """The (method, path) keys of `/api/v1/public/` routes that reach an LLM client."""
    offenders: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith(PUBLIC_API_PREFIX):
            continue
        if route_closure_reaches_llm(route, reached, edges):
            offenders.update((method, route.path) for method in route.methods)
    return offenders


def test_no_public_route_reaches_any_llm_client(
    app: FastAPI,
    reached_llm: set[type],
    di_graph: tuple[dict[type, set[type]], set[type]],
) -> None:
    edges, _ = di_graph
    offenders = public_routes_reaching_llm(app, reached_llm, edges)

    assert not offenders, (
        "public guest routes must make no LLM call (P3); these reach an LLM client: "
        + describe_routes(offenders)
    )


def test_every_llm_reaching_route_requires_a_signed_in_caller(
    app: FastAPI,
    reached_llm: set[type],
    di_graph: tuple[dict[type, set[type]], set[type]],
) -> None:
    edges, _ = di_graph
    offenders: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route_closure_reaches_llm(route, reached_llm, edges):
            continue
        if AI_ROLE_GATE.__name__ not in dependency_call_names(route.dependant):
            offenders.append(f"{sorted(route.methods)} {route.path}")
    assert not offenders, (
        "every LLM-reaching route must belong to a signed-in caller through the "
        "sign-in dependency chain so a guest is asked to sign in and no call is "
        "made: " + "; ".join(offenders)
    )


def test_guest_exam_workspace_routes_are_public_and_llm_free(
    app: FastAPI,
    reached_llm: set[type],
    di_graph: tuple[dict[type, set[type]], set[type]],
) -> None:
    edges, _ = di_graph
    guest_routes = [
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith(GUEST_WORKSPACE_PREFIX)
    ]
    guest_paths = {route.path for route in guest_routes}

    assert guest_routes, "the guest exam-workspace surface disappeared from the public namespace"
    missing = REQUIRED_GUEST_WORKSPACE_PATHS - guest_paths
    assert not missing, "pinned guest exam-workspace routes are missing: " + ", ".join(
        sorted(missing)
    )

    llm_free = all(
        not route_closure_reaches_llm(route, reached_llm, edges) for route in guest_routes
    )
    assert llm_free, "guest exam-workspace routes must make no LLM call (P3): " + describe_routes(
        {
            (method, route.path)
            for route in guest_routes
            if route_closure_reaches_llm(route, reached_llm, edges)
            for method in route.methods
        }
    )

    auth_names = app_auth_dependency_names()
    gated = [
        f"{sorted(route.methods)} {route.path} -> "
        f"{sorted(dependency_call_names(route.dependant) & auth_names)}"
        for route in guest_routes
        if dependency_call_names(route.dependant) & auth_names
    ]
    assert not gated, (
        "guest exam-workspace routes must stay public with no require_app_* "
        "auth dependency: " + "; ".join(gated)
    )


def test_guard_detects_a_public_route_reaching_llm(
    reached_llm: set[type],
    di_graph: tuple[dict[type, set[type]], set[type]],
) -> None:
    edges, _ = di_graph
    router = APIRouter()

    @router.post("/api/v1/public/__guard_probe__/llm")
    async def public_llm_probe(handler: FromDishka[InlineCompletionHandlerProtocol]) -> None:
        del handler

    probe_app = FastAPI()
    probe_app.include_router(router)

    offenders = public_routes_reaching_llm(probe_app, reached_llm, edges)

    assert offenders == {("POST", "/api/v1/public/__guard_probe__/llm")}, (
        "the guard failed its adversarial self-check: a public route reaching "
        "an LLM client was not reported"
    )
