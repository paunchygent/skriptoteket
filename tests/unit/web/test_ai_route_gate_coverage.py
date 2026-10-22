"""Route-coverage guard for paid-LLM sign-in.

Purpose:
    Prove that the set of HTTP routes that can start a paid LLM call, the set
    of routes whose dependency chain reaches the sign-in gate, and an explicit
    expected snapshot are equal. Every paid route must keep a signed-in caller
    behind it, reached directly or through a role check, and no guest or
    public route may reach an LLM client. A new route that reaches an LLM
    client without the sign-in chain fails this module.

Relationships:
    - Maintained policy lives in `ai_route_gate_policy.py`.
    - Discovery and classification helpers live in `ai_route_gate_discovery.py`,
      which derives reachability from `skriptoteket.di.build_providers` and the
      real FastAPI app built by `skriptoteket.web.app.create_app`.
    - Complements the HTTP-level access tests in
      `test_apps_exam_workspace_non_admin_ai_api.py`.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import typing

import pytest
from dishka import Provider, Scope, provide
from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import APIRoute, APIWebSocketRoute

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import ExamAnswerKeySourceKind
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import User
from skriptoteket.infrastructure.llm.openai import decisions_item_labeler
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from skriptoteket.infrastructure.llm.openai.chat_ops_provider import OpenAIChatOpsProvider
from skriptoteket.infrastructure.llm.openai.chat_stream_provider import OpenAIChatStreamProvider
from skriptoteket.infrastructure.llm.openai.inline_completion_provider import (
    OpenAIInlineCompletionProvider,
)
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.identity import HuleEduInternalIdentityVerifierProtocol
from skriptoteket.protocols.item_type_labeler import ExamContentTagClassifierProtocol
from skriptoteket.protocols.llm import InlineCompletionHandlerProtocol
from skriptoteket.protocols.llm_door import LlmDoorClientProtocol
from skriptoteket.protocols.sleeper import SleeperProtocol
from skriptoteket.web.app import create_app
from skriptoteket.web.auth.huleedu_app_projection import (
    require_app_user_api,
)
from skriptoteket.web.dishka_dependencies import FromDishka
from tests.unit.web.ai_route_gate_discovery import (
    ai_gated_route_keys,
    build_di_graph,
    closure,
    code_builds_llm,
    dependency_call_names,
    dependency_types,
    describe_routes,
    is_paid_llm_route,
    llm_client_classes,
    paid_llm_route_keys,
    type_name,
    types_reaching_llm,
)
from tests.unit.web.ai_route_gate_policy import (
    AI_ROLE_GATE,
    EXPECTED_AI_ROUTES,
    JOB_ENQUEUERS,
    JOB_LANES,
    NON_AI_JOB_REPOSITORY_USERS,
    PAID_LLM_PROTOCOLS,
)

pytestmark = pytest.mark.unit


class ContentOnlyProvider(Provider):
    """Probe provider that builds the paid client through a module-qualified name."""

    @provide(scope=Scope.REQUEST)
    def content_only_client(
        self,
        door: LlmDoorClientProtocol,
        settings: Settings,
        sleeper: SleeperProtocol,
    ) -> ExamContentTagClassifierProtocol:
        return decisions_item_labeler.OpenAIDecisionsItemTypeLabeler(
            door=door,
            timeout_seconds=float(settings.LLM_ITEM_LABELER_TIMEOUT_SECONDS),
            sleeper=sleeper,
            max_attempts=1,
        )


@pytest.fixture(scope="module")
def di_graph() -> tuple[dict[type, set[type]], set[type]]:
    return build_di_graph()


@pytest.fixture(scope="module")
def reached_llm(di_graph: tuple[dict[type, set[type]], set[type]]) -> set[type]:
    edges, inline_roots = di_graph
    return types_reaching_llm(edges, inline_roots)


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
            f"the {kind.value} lane {type_name(lane)} no longer reaches an LLM client; "
            "the AI job classification is stale"
        )
    digiexam_lane = JOB_LANES[ExamAnswerKeySourceKind.DIGIEXAM_IMPORT]
    assert digiexam_lane not in reached_llm, (
        f"the digiexam_import lane {type_name(digiexam_lane)} reaches an LLM client; "
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
        for dependency_type in dependency_types(route.dependant):
            if ExamAnswerKeyEnrichmentJobRepositoryProtocol in closure(dependency_type, edges):
                discovered.add(dependency_type)

    expected = set(JOB_ENQUEUERS) | set(NON_AI_JOB_REPOSITORY_USERS)
    missing = expected - discovered
    unknown = discovered - expected
    assert not unknown, "route-resolved job-repository users missing a decision: " + ", ".join(
        sorted(type_name(item) for item in unknown)
    )
    assert not missing, "stale job-repository classification: " + ", ".join(
        sorted(type_name(item) for item in missing)
    )


def test_paid_llm_routes_require_sign_in(app: FastAPI, reached_llm: set[type]) -> None:
    derived = paid_llm_route_keys(app, reached_llm)
    gated = ai_gated_route_keys(app)

    assert derived == EXPECTED_AI_ROUTES, (
        "paid-LLM route snapshot changed; ungated-to-derive: "
        + describe_routes(EXPECTED_AI_ROUTES - derived)
        + "; derived-outside-snapshot: "
        + describe_routes(derived - EXPECTED_AI_ROUTES)
        + " (do not gate a new route here; report it)"
    )
    assert not (EXPECTED_AI_ROUTES - gated), (
        "snapshot paid-LLM routes whose sign-in chain is broken: "
        + describe_routes(EXPECTED_AI_ROUTES - gated)
    )
    assert not (derived - gated), "paid-LLM routes outside the sign-in chain: " + describe_routes(
        derived - gated
    )


def test_no_websocket_route_reaches_llm(app: FastAPI, reached_llm: set[type]) -> None:
    offenders: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIWebSocketRoute):
            continue
        hits = sorted(
            type_name(dependency_type)
            for dependency_type in dependency_types(route.dependant)
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
    ) -> None:
        del handler

    probe_app = FastAPI()
    probe_app.include_router(router)
    probe_route = next(route for route in probe_app.routes if isinstance(route, APIRoute))

    assert is_paid_llm_route(probe_route, reached_llm), (
        "the guard failed its adversarial self-check: an inline-completion route "
        "was not classified as a paid-LLM route"
    )
    assert AI_ROLE_GATE.__name__ not in dependency_call_names(probe_route.dependant), (
        "the guard failed its adversarial self-check: an ungated LLM route was reported as gated"
    )


def test_dependency_types_reads_annotated_types_through_nested_dependencies() -> None:
    router = APIRouter()

    @router.post("/__guard_probe__/dependency-types")
    async def dependency_types_probe(
        handler: FromDishka[InlineCompletionHandlerProtocol],
        user: User = Depends(require_app_user_api),
    ) -> None:
        del handler, user

    probe_app = FastAPI()
    probe_app.include_router(router)
    probe_route = next(route for route in probe_app.routes if isinstance(route, APIRoute))

    found = dependency_types(probe_route.dependant)

    assert InlineCompletionHandlerProtocol in found, (
        "the guard did not read the route's own Annotated Dishka parameter"
    )
    assert HuleEduInternalIdentityVerifierProtocol in found, (
        "the guard did not traverse a nested dependency's Annotated Dishka parameter"
    )


def test_paid_llm_client_classes_include_known_openai_clients() -> None:
    expected = {
        OpenAIInlineCompletionProvider,
        OpenAIChatStreamProvider,
        OpenAIChatOpsProvider,
        OpenAIAnswerKeyStructuredProvider,
        decisions_item_labeler.OpenAIDecisionsItemTypeLabeler,
    }
    missing = expected - llm_client_classes()
    assert not missing, (
        "PAID_LLM_PROTOCOLS no longer derives these LLM clients as paid roots: "
        + ", ".join(sorted(type_name(item) for item in missing))
    )


def protocol_classes() -> list[type]:
    """Every Protocol defined in a `skriptoteket.protocols` module with members."""
    import skriptoteket.protocols as protocols_package

    found: list[type] = []
    modules = pkgutil.walk_packages(protocols_package.__path__, protocols_package.__name__ + ".")
    for module_info in modules:
        module = importlib.import_module(module_info.name)
        for _, candidate in inspect.getmembers(module, inspect.isclass):
            if candidate.__module__ != module.__name__:
                continue
            if typing.is_protocol(candidate) and typing.get_protocol_members(candidate):
                found.append(candidate)
    return found


def test_paid_llm_clients_structurally_cover_their_protocols() -> None:
    known_clients = (
        OpenAIInlineCompletionProvider,
        OpenAIChatStreamProvider,
        OpenAIChatOpsProvider,
        OpenAIAnswerKeyStructuredProvider,
        decisions_item_labeler.OpenAIDecisionsItemTypeLabeler,
    )
    protocols = protocol_classes()
    missing: list[str] = []
    for client in known_clients:
        for protocol in protocols:
            members = typing.get_protocol_members(protocol)
            if not all(hasattr(client, member) for member in members):
                continue
            if protocol in PAID_LLM_PROTOCOLS:
                continue
            missing.append(f"{client.__name__} -> {protocol.__module__}.{protocol.__qualname__}")
    assert not missing, (
        "paid LLM clients structurally satisfy protocols absent from PAID_LLM_PROTOCOLS: "
        + ", ".join(sorted(missing))
    )


def test_code_builds_llm_sees_module_qualified_constructor() -> None:
    (factory,) = ContentOnlyProvider().factories
    assert code_builds_llm(factory.source), (
        "the guard does not see a paid client built with a module-qualified constructor"
    )


def test_content_classifier_protocol_route_is_paid_and_ungated(
    reached_llm: set[type],
) -> None:
    router = APIRouter()

    @router.post("/__guard_probe__/content-classification")
    async def content_classification_probe(
        classifier: FromDishka[ExamContentTagClassifierProtocol],
    ) -> None:
        del classifier

    probe_app = FastAPI()
    probe_app.include_router(router)
    probe_route = next(route for route in probe_app.routes if isinstance(route, APIRoute))

    assert is_paid_llm_route(probe_route, reached_llm), (
        "the guard failed its adversarial self-check: a route reaching "
        "ExamContentTagClassifierProtocol was not classified as a paid-LLM route"
    )
    assert AI_ROLE_GATE.__name__ not in dependency_call_names(probe_route.dependant), (
        "the guard failed its adversarial self-check: the content-classification "
        "probe route was reported as gated"
    )
