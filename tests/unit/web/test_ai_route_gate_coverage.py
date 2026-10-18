"""Route-coverage guard for the paid-AI admin gate.

Purpose:
    Prove (TASK-SKRIPT-REP-0044 L1, L2, L4) that the set of HTTP routes that can
    start a paid LLM call, the set of routes carrying `require_app_ai_api`, and
    an explicit expected snapshot are equal. A new route that reaches an LLM
    client without the gate fails this module.

Relationships:
    - Maintained policy lives in `ai_route_gate_policy.py`.
    - Discovery and classification helpers live in `ai_route_gate_discovery.py`,
      which derives reachability from `skriptoteket.di.build_providers` and the
      real FastAPI app built by `skriptoteket.web.app.create_app`.
    - Complements the HTTP-level gate tests in
      `test_apps_exam_workspace_ai_gate_api.py`.
"""

from __future__ import annotations

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import APIRoute, APIWebSocketRoute

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import ExamAnswerKeySourceKind
from skriptoteket.domain.identity.models import User
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from skriptoteket.infrastructure.llm.openai.chat_ops_provider import OpenAIChatOpsProvider
from skriptoteket.infrastructure.llm.openai.chat_stream_provider import OpenAIChatStreamProvider
from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    OpenAIDecisionsItemTypeLabeler,
)
from skriptoteket.infrastructure.llm.openai.inline_completion_provider import (
    OpenAIInlineCompletionProvider,
)
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.identity import HuleEduInternalIdentityVerifierProtocol
from skriptoteket.protocols.llm import InlineCompletionHandlerProtocol
from skriptoteket.web.app import create_app
from skriptoteket.web.auth.huleedu_app_projection import (
    require_app_contributor_api,
    require_app_user_api,
)
from skriptoteket.web.dishka_dependencies import FromDishka
from tests.unit.web.ai_route_gate_discovery import (
    ai_gated_route_keys,
    build_di_graph,
    closure,
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
    FORBIDDEN_AI_ROLE_GATES,
    JOB_ENQUEUERS,
    JOB_LANES,
    NON_AI_JOB_REPOSITORY_USERS,
)

pytestmark = pytest.mark.unit


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


def test_paid_llm_routes_require_ai_gate(app: FastAPI, reached_llm: set[type]) -> None:
    derived = paid_llm_route_keys(app, reached_llm)
    gated = ai_gated_route_keys(app)

    assert derived == EXPECTED_AI_ROUTES, (
        "paid-LLM route snapshot changed; ungated-to-derive: "
        + describe_routes(EXPECTED_AI_ROUTES - derived)
        + "; derived-outside-snapshot: "
        + describe_routes(derived - EXPECTED_AI_ROUTES)
        + " (do not gate a new route here; report it)"
    )
    assert gated == EXPECTED_AI_ROUTES, (
        "routes carrying require_app_ai_api deviate from the snapshot; not-yet-gated: "
        + describe_routes(EXPECTED_AI_ROUTES - gated)
        + "; gated-outside-snapshot: "
        + describe_routes(gated - EXPECTED_AI_ROUTES)
    )
    assert derived == gated, (
        "paid-LLM routes without the AI gate: "
        + describe_routes(derived - gated)
        + "; gated routes that cannot start an LLM call: "
        + describe_routes(gated - derived)
    )


def test_ai_routes_have_no_other_role_dependency(app: FastAPI, reached_llm: set[type]) -> None:
    offenders: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not is_paid_llm_route(route, reached_llm):
            continue
        conflicting = dependency_call_names(route.dependant) & FORBIDDEN_AI_ROLE_GATES
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
        user: User = Depends(require_app_contributor_api),
    ) -> None:
        del handler, user

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
        OpenAIDecisionsItemTypeLabeler,
    }
    missing = expected - llm_client_classes()
    assert not missing, (
        "PAID_LLM_PROTOCOLS no longer derives these LLM clients as paid roots: "
        + ", ".join(sorted(type_name(item) for item in missing))
    )
