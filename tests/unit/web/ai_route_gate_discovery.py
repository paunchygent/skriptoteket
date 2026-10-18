"""Discovery and classification helpers for the paid-AI route-coverage guard.

Purpose:
    Derive, from the real production wiring, the set of DI types that reach a
    paid LLM client and the HTTP routes that can therefore start a paid call,
    plus the auxiliary scans the guard uses to classify job lanes and gate
    routes. None of the numbers here are maintained by hand; every result is
    computed from `skriptoteket.di.build_providers`, the real FastAPI app and
    the bytecode of provider factories.

Relationships:
    - Reads the maintained policy from `ai_route_gate_policy.py`.
    - Consumed by `test_ai_route_gate_coverage.py`.
    - Derives reachability from `skriptoteket.di.build_providers`; `build_providers`
      is imported here so probes can patch
      `ai_route_gate_discovery.build_providers`.
    - Reads the resolved Dishka type that
      `skriptoteket.web.dishka_dependencies.from_dishka` records on each inner
      FastAPI dependency.
"""

from __future__ import annotations

import functools
import importlib
import inspect
import pkgutil
import types
from collections.abc import Iterator, Set

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from skriptoteket.config import Settings
from skriptoteket.di import build_providers
from tests.unit.web.ai_route_gate_policy import (
    AI_ROLE_GATE,
    JOB_ENQUEUERS,
    PAID_LLM_PROTOCOLS,
)


def type_name(value: object) -> str:
    return getattr(value, "__name__", str(value))


def paid_llm_client_classes() -> set[type]:
    """Every class under `skriptoteket.infrastructure.llm` implementing a paid protocol."""
    import skriptoteket.infrastructure.llm as llm_package

    found: set[type] = set()
    modules = pkgutil.walk_packages(llm_package.__path__, llm_package.__name__ + ".")
    for module_info in modules:
        module = importlib.import_module(module_info.name)
        for _, candidate in inspect.getmembers(module, inspect.isclass):
            if candidate.__module__ != module.__name__:
                continue
            if any(protocol in candidate.__mro__[1:] for protocol in PAID_LLM_PROTOCOLS):
                found.add(candidate)
    return found


@functools.cache
def llm_client_classes() -> set[type]:
    return paid_llm_client_classes()


def code_builds_llm(source: object, seen: set[object] | None = None) -> bool:
    """True when a factory body references an LLM client class, following di helpers."""
    seen = set() if seen is None else seen
    function = getattr(source, "__func__", source)
    code = getattr(function, "__code__", None)
    if code is None or function in seen:
        return False
    seen.add(function)

    globals_ = getattr(function, "__globals__", {})
    names = set(code.co_names)
    for constant in code.co_consts:
        if isinstance(constant, types.CodeType):
            names |= set(constant.co_names)

    llm_classes = llm_client_classes()
    for name in names:
        referenced = globals_.get(name)
        if referenced in llm_classes:
            return True
        if (
            isinstance(referenced, types.FunctionType)
            and referenced.__module__.startswith("skriptoteket.di")
            and code_builds_llm(referenced, seen)
        ):
            return True
    return False


def build_di_graph() -> tuple[dict[type, set[type]], set[type]]:
    """Provider dependency edges plus the factories that inline an LLM client."""
    edges: dict[type, set[type]] = {}
    inline_roots: set[type] = set()
    for provider in build_providers(Settings()):
        for factory in provider.factories:
            provided = factory.provides.type_hint
            dependencies = [dependency.type_hint for dependency in factory.dependencies]
            dependencies.extend(
                dependency.type_hint for dependency in factory.kw_dependencies.values()
            )
            edges.setdefault(provided, set()).update(dependencies)
            if code_builds_llm(factory.source):
                inline_roots.add(provided)
        for alias in provider.aliases:
            edges.setdefault(alias.provides.type_hint, set()).add(alias.source.type_hint)
    return edges, inline_roots


def types_reaching_llm(edges: dict[type, set[type]], inline_roots: set[type]) -> set[type]:
    """Fixed point of every DI type that depends, directly or not, on an LLM root."""
    reverse: dict[type, set[type]] = {}
    for source, dependencies in edges.items():
        for dependency in dependencies:
            reverse.setdefault(dependency, set()).add(source)

    reached = set(PAID_LLM_PROTOCOLS) | set(inline_roots)
    pending = list(reached)
    while pending:
        current = pending.pop()
        for parent in reverse.get(current, ()):
            if parent not in reached:
                reached.add(parent)
                pending.append(parent)
    return reached


def closure(root: type, edges: dict[type, set[type]]) -> set[type]:
    seen: set[type] = set()
    pending = [root]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(edges.get(current, ()))
    return seen


def iter_dependant(dependant: Dependant) -> Iterator[Dependant]:
    yield dependant
    for child in dependant.dependencies:
        yield from iter_dependant(child)


def dishka_types(dependant: Dependant) -> set[type]:
    found: set[type] = set()
    for dependency in iter_dependant(dependant):
        resolved = getattr(dependency.call, "dishka_dependency_type", None)
        if resolved is not None:
            found.add(resolved)
    return found


def dependency_call_names(dependant: Dependant) -> set[str]:
    names: set[str] = set()
    for dependency in iter_dependant(dependant):
        name = getattr(dependency.call, "__name__", None)
        if isinstance(name, str):
            names.add(name)
    return names


def is_paid_llm_route(route: APIRoute, reached: set[type]) -> bool:
    return any(
        dependency_type in reached or dependency_type in JOB_ENQUEUERS
        for dependency_type in dishka_types(route.dependant)
    )


def paid_llm_route_keys(app: FastAPI, reached: set[type]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if is_paid_llm_route(route, reached):
            keys.update((method, route.path) for method in route.methods)
    return keys


def ai_gated_route_keys(app: FastAPI) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if AI_ROLE_GATE.__name__ in dependency_call_names(route.dependant):
            keys.update((method, route.path) for method in route.methods)
    return keys


def describe_routes(routes: Set[tuple[str, str]]) -> str:
    if not routes:
        return "none"
    return ", ".join(f"{method} {path}" for method, path in sorted(routes))
