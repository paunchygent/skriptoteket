"""Route-coverage guard for the paid-AI admin gate.

Purpose:
    Prove (TASK-SKRIPT-REP-0044 L1, L2, L4) that the set of HTTP routes that can
    start a paid LLM call, the set of routes carrying `require_app_ai_api`, and
    an explicit expected snapshot are equal. A new route that reaches an LLM
    client without the gate fails this module.

Relationships:
    - Derives reachability from `skriptoteket.di.build_providers` and the real
      FastAPI app built by `skriptoteket.web.app.create_app`.
    - Reads the resolved Dishka type that
      `skriptoteket.web.dishka_dependencies.from_dishka` records on each inner
      FastAPI dependency.
    - Complements the HTTP-level gate tests in
      `test_apps_exam_workspace_ai_gate_api.py`.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import types
from collections.abc import Iterator

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, APIWebSocketRoute

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import ExamAnswerKeySourceKind
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_content_tags import (
    GetExamContentSuggestionsHandler,
    ProcessExamContentSuggestionsHandler,
    RequestExamContentSuggestionsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_digiexam_jobs import (
    ProcessExamWorkspaceDigiExamJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.config import Settings
from skriptoteket.di import build_providers
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols import llm as llm_protocols
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyStructuredProviderProtocol,
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
)
from skriptoteket.protocols.exam_workspace import (
    GetExamWorkspaceAnswerKeySuggestionsStatusHandlerProtocol,
    GetExamWorkspaceConversionStatusHandlerProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
    ImportExamWorkspaceDigiExamDocumentHandlerProtocol,
    ImportExamWorkspaceDocumentHandlerProtocol,
    RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol,
    SaveExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_change_type import (
    ChangeExamWorkspaceItemTypeHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_history import (
    StoreExamWorkspaceUndoStepHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_parents import ExamWorkspaceParentsHandlerProtocol
from skriptoteket.protocols.item_type_labeler import (
    MeteredItemTypeLabelerProtocol,
    SecondPassItemTypeLabelerProtocol,
)
from skriptoteket.protocols.llm import InlineCompletionHandlerProtocol
from skriptoteket.web.app import create_app
from skriptoteket.web.auth.huleedu_app_projection import (
    require_app_admin_api,
    require_app_ai_api,
    require_app_contributor_api,
    require_app_superuser_api,
)
from skriptoteket.web.dishka_dependencies import FromDishka

pytestmark = pytest.mark.unit

# The one maintained input: the paid LLM client protocols. Every class under
# `skriptoteket.infrastructure.llm` that implements one of these is a paid LLM
# client, and every DI type whose closure reaches one is an AI type.
PAID_LLM_PROTOCOLS: frozenset[type] = frozenset(
    {
        AnswerKeyStructuredProviderProtocol,
        MeteredItemTypeLabelerProtocol,
        SecondPassItemTypeLabelerProtocol,
        llm_protocols.InlineCompletionProvidersProtocol,
        llm_protocols.ChatStreamProvidersProtocol,
        llm_protocols.ChatOpsProvidersProtocol,
    }
)

# Route-resolved handlers that enqueue a job the execution worker runs. Their
# own call path stops at enqueue, so the lane below decides whether the job
# spends money.
JOB_ENQUEUERS: dict[type, ExamAnswerKeySourceKind] = {
    RequestExamContentSuggestionsHandler: ExamAnswerKeySourceKind.CONTENT_TAGS,
    ImportExamWorkspaceDocumentHandlerProtocol: ExamAnswerKeySourceKind.DOCX_IMPORT,
    RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol: ExamAnswerKeySourceKind.WORKSPACE,
}

# The worker handler each enqueued job kind runs.
JOB_LANES: dict[ExamAnswerKeySourceKind, type] = {
    ExamAnswerKeySourceKind.CONTENT_TAGS: ProcessExamContentSuggestionsHandler,
    ExamAnswerKeySourceKind.DOCX_IMPORT: ProcessExamWorkspaceDocxJobHandler,
    ExamAnswerKeySourceKind.WORKSPACE: ProcessExamAnswerKeyEnrichmentJobHandler,
    ExamAnswerKeySourceKind.DIGIEXAM_IMPORT: ProcessExamWorkspaceDigiExamJobHandler,
}

# Route-resolved Dishka types that use the exam answer-key job repository but
# make no LLM call. A new entry here is a decision: either it is a job enqueuer
# or the canonical gate test below also fails.
NON_AI_JOB_REPOSITORY_USERS: dict[type, str] = {
    ChangeExamWorkspaceItemTypeHandlerProtocol: "re-types one already-parsed item; no LLM call",
    ExamWorkspaceParentsHandlerProtocol: "reads the saved document and undo steps; no LLM call",
    GetExamContentSuggestionsHandler: ("reads an enqueued content-tag job's status; no LLM call"),
    GetExamWorkspaceAnswerKeySuggestionsStatusHandlerProtocol: (
        "reads an enqueued suggestion job's status; no LLM call"
    ),
    GetExamWorkspaceConversionStatusHandlerProtocol: "polls conversion progress; no LLM call",
    GetExamWorkspaceDocumentHandlerProtocol: "reopens the saved document; no LLM call",
    ImportExamWorkspaceDigiExamDocumentHandlerProtocol: (
        "enqueues DIGIEXAM_IMPORT, whose lane makes no LLM call"
    ),
    SaveExamWorkspaceDocumentHandlerProtocol: (
        "saves, copies and reads document history; no LLM call"
    ),
    StoreExamWorkspaceUndoStepHandlerProtocol: "stores an autosave undo step; no LLM call",
}

# The routes that can start a paid LLM call today, as (method, path) pairs.
EXPECTED_AI_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/api/v1/editor/completions"),
        ("POST", "/api/v1/editor/edit-ops"),
        ("POST", "/api/v1/editor/tools/{tool_id}/chat"),
        ("POST", "/api/v1/apps/documents.conversion_hub/exam-workspace/documents"),
        (
            "POST",
            "/api/v1/apps/documents.conversion_hub/exam-workspace"
            "/documents/{lineage_id}/items/retry",
        ),
        (
            "POST",
            "/api/v1/apps/documents.conversion_hub/exam-workspace"
            "/documents/{lineage_id}/content-suggestions",
        ),
        (
            "POST",
            "/api/v1/apps/documents.conversion_hub/exam-workspace"
            "/documents/{lineage_id}/answer-key-suggestions",
        ),
    }
)

_AI_ROLE_GATE = require_app_ai_api
_FORBIDDEN_AI_ROLE_GATES = frozenset(
    {
        require_app_contributor_api.__name__,
        require_app_admin_api.__name__,
        require_app_superuser_api.__name__,
    }
)

_LLM_CLIENT_CLASSES: set[type] | None = None


def _type_name(value: object) -> str:
    return getattr(value, "__name__", str(value))


def _paid_llm_client_classes() -> set[type]:
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


def _llm_client_classes() -> set[type]:
    global _LLM_CLIENT_CLASSES
    if _LLM_CLIENT_CLASSES is None:
        _LLM_CLIENT_CLASSES = _paid_llm_client_classes()
    return _LLM_CLIENT_CLASSES


def _code_builds_llm(source: object, seen: set[object] | None = None) -> bool:
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

    llm_classes = _llm_client_classes()
    for name in names:
        referenced = globals_.get(name)
        if referenced in llm_classes:
            return True
        if (
            isinstance(referenced, types.FunctionType)
            and referenced.__module__.startswith("skriptoteket.di")
            and _code_builds_llm(referenced, seen)
        ):
            return True
    return False


def _build_di_graph() -> tuple[dict[type, set[type]], set[type]]:
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
            if _code_builds_llm(factory.source):
                inline_roots.add(provided)
        for alias in provider.aliases:
            edges.setdefault(alias.provides.type_hint, set()).add(alias.source.type_hint)
    return edges, inline_roots


def _types_reaching_llm(edges: dict[type, set[type]], inline_roots: set[type]) -> set[type]:
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


def _closure(root: type, edges: dict[type, set[type]]) -> set[type]:
    seen: set[type] = set()
    pending = [root]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(edges.get(current, ()))
    return seen


def _iter_dependant(dependant: Dependant) -> Iterator[Dependant]:
    yield dependant
    for child in dependant.dependencies:
        yield from _iter_dependant(child)


def _dishka_types(dependant: Dependant) -> set[type]:
    found: set[type] = set()
    for dependency in _iter_dependant(dependant):
        resolved = getattr(dependency.call, "dishka_dependency_type", None)
        if resolved is not None:
            found.add(resolved)
    return found


def _dependency_call_names(dependant: Dependant) -> set[str]:
    names: set[str] = set()
    for dependency in _iter_dependant(dependant):
        name = getattr(dependency.call, "__name__", None)
        if isinstance(name, str):
            names.add(name)
    return names


def _is_paid_llm_route(route: APIRoute, reached: set[type]) -> bool:
    return any(
        dependency_type in reached or dependency_type in JOB_ENQUEUERS
        for dependency_type in _dishka_types(route.dependant)
    )


def _paid_llm_route_keys(app: FastAPI, reached: set[type]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if _is_paid_llm_route(route, reached):
            keys.update((method, route.path) for method in route.methods)
    return keys


def _ai_gated_route_keys(app: FastAPI) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if _AI_ROLE_GATE.__name__ in _dependency_call_names(route.dependant):
            keys.update((method, route.path) for method in route.methods)
    return keys


@pytest.fixture(scope="module")
def di_graph() -> tuple[dict[type, set[type]], set[type]]:
    return _build_di_graph()


@pytest.fixture(scope="module")
def reached_llm(di_graph: tuple[dict[type, set[type]], set[type]]) -> set[type]:
    edges, inline_roots = di_graph
    return _types_reaching_llm(edges, inline_roots)


@pytest.fixture(scope="module")
def app() -> FastAPI:
    return create_app()


def test_job_lanes_match_llm_reach(reached_llm: set[type]) -> None:
    spending_kinds = (
        ExamAnswerKeySourceKind.CONTENT_TAGS,
        ExamAnswerKeySourceKind.DOCX_IMPORT,
        ExamAnswerKeySourceKind.WORKSPACE,
    )
    for kind in spending_kinds:
        lane = JOB_LANES[kind]
        assert lane in reached_llm, (
            f"the {kind.value} lane {_type_name(lane)} no longer reaches an LLM client; "
            "the AI job classification is stale"
        )
    digiexam_lane = JOB_LANES[ExamAnswerKeySourceKind.DIGIEXAM_IMPORT]
    assert digiexam_lane not in reached_llm, (
        f"the digiexam_import lane {_type_name(digiexam_lane)} reaches an LLM client; "
        "DigiExam import must stay open"
    )


def test_route_resolved_job_repository_users_are_classified(
    app: FastAPI,
    di_graph: tuple[dict[type, set[type]], set[type]],
) -> None:
    edges, _ = di_graph
    assert all(reason.strip() for reason in NON_AI_JOB_REPOSITORY_USERS.values()), (
        "every non-AI job-repository user needs a one-line reason"
    )

    discovered: set[type] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for dependency_type in _dishka_types(route.dependant):
            if ExamAnswerKeyEnrichmentJobRepositoryProtocol in _closure(dependency_type, edges):
                discovered.add(dependency_type)

    expected = set(JOB_ENQUEUERS) | set(NON_AI_JOB_REPOSITORY_USERS)
    missing = expected - discovered
    unknown = discovered - expected
    assert not unknown, "route-resolved job-repository users missing a decision: " + ", ".join(
        sorted(_type_name(item) for item in unknown)
    )
    assert not missing, "stale job-repository classification: " + ", ".join(
        sorted(_type_name(item) for item in missing)
    )


def test_paid_llm_routes_require_ai_gate(app: FastAPI, reached_llm: set[type]) -> None:
    derived = _paid_llm_route_keys(app, reached_llm)
    gated = _ai_gated_route_keys(app)

    assert derived == EXPECTED_AI_ROUTES, (
        "paid-LLM route snapshot changed; ungated-to-derive: "
        + _describe_routes(EXPECTED_AI_ROUTES - derived)
        + "; derived-outside-snapshot: "
        + _describe_routes(derived - EXPECTED_AI_ROUTES)
        + " (do not gate a new route here; report it)"
    )
    assert gated == EXPECTED_AI_ROUTES, (
        "routes carrying require_app_ai_api deviate from the snapshot; not-yet-gated: "
        + _describe_routes(EXPECTED_AI_ROUTES - gated)
        + "; gated-outside-snapshot: "
        + _describe_routes(gated - EXPECTED_AI_ROUTES)
    )
    assert derived == gated, (
        "paid-LLM routes without the AI gate: "
        + _describe_routes(derived - gated)
        + "; gated routes that cannot start an LLM call: "
        + _describe_routes(gated - derived)
    )


def test_ai_routes_have_no_other_role_dependency(app: FastAPI, reached_llm: set[type]) -> None:
    offenders: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not _is_paid_llm_route(route, reached_llm):
            continue
        conflicting = _dependency_call_names(route.dependant) & _FORBIDDEN_AI_ROLE_GATES
        if conflicting:
            offenders.append(f"{sorted(route.methods)} {route.path} -> {sorted(conflicting)}")
    assert not offenders, (
        "paid-LLM routes must carry require_app_ai_api as their only AI role check: "
        + "; ".join(offenders)
    )


def test_no_websocket_route_reaches_llm(app: FastAPI, reached_llm: set[type]) -> None:
    offenders: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIWebSocketRoute):
            continue
        hits = sorted(
            _type_name(dependency_type)
            for dependency_type in _dishka_types(route.dependant)
            if dependency_type in reached_llm or dependency_type in JOB_ENQUEUERS
        )
        if hits:
            offenders.append(f"{route.path} -> {hits}")
    assert not offenders, "no websocket route may reach an LLM client (L4): " + "; ".join(offenders)


def test_guard_detects_an_ungated_llm_route(reached_llm: set[type]) -> None:
    router = APIRouter()

    @router.post("/__guard_probe__/ungated-llm")
    async def ungated_llm_probe(
        handler: FromDishka[InlineCompletionHandlerProtocol],
        user: User = Depends(require_app_contributor_api),
    ) -> None:
        del handler, user

    probe_app = FastAPI()
    probe_app.include_router(router)
    probe_route = next(route for route in probe_app.routes if isinstance(route, APIRoute))

    assert _is_paid_llm_route(probe_route, reached_llm), (
        "the guard failed its adversarial self-check: an inline-completion route "
        "was not classified as a paid-LLM route"
    )
    assert _AI_ROLE_GATE.__name__ not in _dependency_call_names(probe_route.dependant), (
        "the guard failed its adversarial self-check: an ungated LLM route was reported as gated"
    )


def _describe_routes(routes: set[tuple[str, str]]) -> str:
    if not routes:
        return "none"
    return ", ".join(f"{method} {path}" for method, path in sorted(routes))
