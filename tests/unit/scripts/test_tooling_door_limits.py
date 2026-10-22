"""Agent tooling never crosses the free pool without the user's explicit approval.

Each tool builds one door caller for the whole invocation through
``tooling_caller``: without ``--allow-paid-overage`` every call sends
``free_allowance_only`` and a pool refusal stops the run with the approval
message; with the flag every call sends ``allow_paid_overage``. The
conversion eval additionally carries a typed pipeline limit to its CLI limit
handler instead of filing it as a crash. All three tools drive the real
``HuleEduLlmDoorClient`` over ``httpx.MockTransport`` below.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest

from scripts.exam_conversion_eval import __main__ as eval_main
from scripts.item_type_labeler_live import __main__ as live_main
from scripts.labeling_feasibility import __main__ as feasibility_main
from scripts.labeling_feasibility.api import OpenAIClient
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
    StructuredLLMReasoningEffort,
    StructuredLLMRequest,
    StructuredOutputSpec,
)
from skriptoteket.domain.llm_door import AiDailyLimit, AiDailyLimitReached, tooling_caller
from skriptoteket.infrastructure.llm.door.client import HuleEduLlmDoorClient
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    OpenAIDecisionsItemTypeLabeler,
)
from skriptoteket.infrastructure.time.asyncio_sleeper import AsyncioSleeper
from skriptoteket.protocols.item_type_labeler import LabelingItem, LabelingRequest

pytestmark = pytest.mark.unit

USER_ID = UUID("22222222-2222-2222-2222-222222222222")
_POOL_BODY = {
    "error": {
        "type": "huleedu_openai_door",
        "code": "openai_complimentary_allowance_exceeded",
        "limit": "pool",
    }
}
_USER_SHARE_BODY = {
    "error": {
        "type": "huleedu_openai_door",
        "code": "openai_caller_user_share_exceeded",
        "limit": "user_share",
    }
}
_APPROVAL_TEXT = "rerun with --allow-paid-overage only after the user says yes."
_DOCX = Path(
    "tests/fixtures/exam_conversion/docx_corpus/metodprov_vetenskaplig_metod_med_facit.docx"
)


def _door(
    replies: list[Callable[[], httpx.Response]],
) -> tuple[HuleEduLlmDoorClient, list[str]]:
    """A real door client with scripted replies, recording each call's allowance mode."""
    modes: list[str] = []
    pending = list(replies)

    def handle(request: httpx.Request) -> httpx.Response:
        modes.append(request.headers["X-HuleEdu-OpenAI-Allowance-Mode"])
        return pending.pop(0)()

    return (
        HuleEduLlmDoorClient(
            client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
            base_url="http://door.test:8080",
            internal_api_key="internal-key",
            job_overage_cap_usd_micros=1_000_000,
        ),
        modes,
    )


def _ok(body: object) -> Callable[[], httpx.Response]:
    return lambda: httpx.Response(200, json=body)


def _pool_refusal() -> Callable[[], httpx.Response]:
    return lambda: httpx.Response(429, json=_POOL_BODY)


def _user_share_refusal() -> Callable[[], httpx.Response]:
    return lambda: httpx.Response(429, json=_USER_SHARE_BODY)


def _answer_key_request() -> StructuredLLMRequest:
    return StructuredLLMRequest(
        job_id="job-1",
        item_id="item-1",
        item_type="single_choice",
        prompt_template_version="v1",
        system_prompt="system",
        user_payload="user",
        output_spec=StructuredOutputSpec(
            schema_name="answer",
            schema_version="v1",
            json_schema={
                "type": "object",
                "properties": {"choice": {"type": "string"}},
                "additionalProperties": False,
            },
        ),
        estimated_input_tokens=10,
        max_output_tokens=64,
    )


def _answer_key_profile() -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="openai-gpt-6-luna-answer-key",
        model="gpt-6-luna",
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        is_remote=True,
        context_window_tokens=32_768,
        max_output_tokens=4_096,
        reasoning_effort=StructuredLLMReasoningEffort.LOW,
    )


def _label_request(*, approved: bool) -> LabelingRequest:
    return LabelingRequest(
        job_id=uuid4(),
        items=(LabelingItem(item_id="exam/q1", source_text="Mark one.\nA. Yes\nB. No"),),
        caller=tooling_caller(user_id=USER_ID, paid_overage_approved=approved),
    )


async def test_feasibility_tooling_without_approval_sends_free_only_and_stops_at_pool() -> None:
    door, modes = _door([_ok({"ok": True}), _pool_refusal()])
    tool = OpenAIClient(
        door=door,
        caller=tooling_caller(user_id=USER_ID, paid_overage_approved=False),
        timeout=5.0,
    )
    first = await tool.decisions(label="one", input_value="Mark one.", questions=[])
    assert first.ok
    with pytest.raises(AiDailyLimitReached) as raised:
        await tool.decisions(label="two", input_value="Mark one.", questions=[])
    assert raised.value.limit is AiDailyLimit.POOL
    assert modes == ["free_allowance_only", "free_allowance_only"]


async def test_feasibility_tooling_with_approval_sends_overage_on_both_calls() -> None:
    door, modes = _door([_ok({"ok": True}), _pool_refusal()])
    tool = OpenAIClient(
        door=door,
        caller=tooling_caller(user_id=USER_ID, paid_overage_approved=True),
        timeout=5.0,
    )
    assert (await tool.decisions(label="one", input_value="Mark one.", questions=[])).ok
    with pytest.raises(AiDailyLimitReached):
        await tool.decisions(label="two", input_value="Mark one.", questions=[])
    assert modes == ["allow_paid_overage", "allow_paid_overage"]


async def test_labeler_tooling_without_approval_sends_free_only_and_stops_at_pool() -> None:
    door, modes = _door(
        [_ok({"answers": [{"name": "kind_q1", "type": "refusal"}]}), _pool_refusal()]
    )
    caller = tooling_caller(user_id=USER_ID, paid_overage_approved=False)
    labeler = OpenAIDecisionsItemTypeLabeler(
        door=door, timeout_seconds=5.0, sleeper=AsyncioSleeper()
    )
    labeling = await labeler.label(
        request=LabelingRequest(
            job_id=uuid4(), items=_label_request(approved=False).items, caller=caller
        )
    )
    assert len(labeling.results) == 1
    with pytest.raises(AiDailyLimitReached) as raised:
        await labeler.label(
            request=LabelingRequest(
                job_id=uuid4(), items=_label_request(approved=False).items, caller=caller
            )
        )
    assert raised.value.limit is AiDailyLimit.POOL
    assert modes == ["free_allowance_only", "free_allowance_only"]


async def test_labeler_tooling_with_approval_sends_overage_on_both_calls() -> None:
    door, modes = _door(
        [_ok({"answers": [{"name": "kind_q1", "type": "refusal"}]}), _pool_refusal()]
    )
    caller = tooling_caller(user_id=USER_ID, paid_overage_approved=True)
    labeler = OpenAIDecisionsItemTypeLabeler(
        door=door, timeout_seconds=5.0, sleeper=AsyncioSleeper()
    )
    await labeler.label(
        request=LabelingRequest(
            job_id=uuid4(), items=_label_request(approved=True).items, caller=caller
        )
    )
    with pytest.raises(AiDailyLimitReached):
        await labeler.label(
            request=LabelingRequest(
                job_id=uuid4(), items=_label_request(approved=True).items, caller=caller
            )
        )
    assert modes == ["allow_paid_overage", "allow_paid_overage"]


async def test_eval_provider_without_approval_sends_free_only_and_stops_at_pool() -> None:
    door, modes = _door(
        [_ok({"status": "completed", "output_text": json.dumps({"choice": "a"})}), _pool_refusal()]
    )
    recorder = eval_main._RecordingProvider(
        OpenAIAnswerKeyStructuredProvider(door=door, timeout_seconds=5.0)
    )
    caller = tooling_caller(user_id=USER_ID, paid_overage_approved=False)
    first = await recorder.complete_structured(
        request=_answer_key_request(), profile=_answer_key_profile(), caller=caller
    )
    assert first.content == {"choice": "a"}
    with pytest.raises(AiDailyLimitReached) as raised:
        await recorder.complete_structured(
            request=_answer_key_request(), profile=_answer_key_profile(), caller=caller
        )
    assert raised.value.limit is AiDailyLimit.POOL
    assert modes == ["free_allowance_only", "free_allowance_only"]


async def test_eval_provider_with_approval_sends_overage_on_both_calls() -> None:
    door, modes = _door(
        [_ok({"status": "completed", "output_text": json.dumps({"choice": "a"})}), _pool_refusal()]
    )
    recorder = eval_main._RecordingProvider(
        OpenAIAnswerKeyStructuredProvider(door=door, timeout_seconds=5.0)
    )
    caller = tooling_caller(user_id=USER_ID, paid_overage_approved=True)
    await recorder.complete_structured(
        request=_answer_key_request(), profile=_answer_key_profile(), caller=caller
    )
    with pytest.raises(AiDailyLimitReached):
        await recorder.complete_structured(
            request=_answer_key_request(), profile=_answer_key_profile(), caller=caller
        )
    assert modes == ["allow_paid_overage", "allow_paid_overage"]


def _eval_recorder(door: HuleEduLlmDoorClient) -> eval_main._RecordingProvider:
    return eval_main._RecordingProvider(
        OpenAIAnswerKeyStructuredProvider(door=door, timeout_seconds=5.0)
    )


def _eval_settings() -> Settings:
    """The eval converts with the job's composition whatever the local enable flag says."""

    return Settings().model_copy(update={"LLM_ANSWER_KEY_ENABLED": True})


async def test_full_eval_pool_refusal_reaches_exit_2_with_approval_text(
    capsys: pytest.CaptureFixture[str],
) -> None:
    door, _ = _door([_pool_refusal()])
    with pytest.raises(AiDailyLimitReached) as raised:
        await eval_main._evaluate(
            _DOCX,
            door,
            _eval_settings(),
            _eval_recorder(door),
            tooling_caller(user_id=USER_ID, paid_overage_approved=False),
        )
    assert raised.value.limit is AiDailyLimit.POOL
    assert eval_main._limit_exit(raised.value) == 2
    assert _APPROVAL_TEXT in capsys.readouterr().out


async def test_full_eval_user_share_refusal_reaches_exit_1_naming_the_limit(
    capsys: pytest.CaptureFixture[str],
) -> None:
    door, _ = _door([_user_share_refusal()])
    with pytest.raises(AiDailyLimitReached) as raised:
        await eval_main._evaluate(
            _DOCX,
            door,
            _eval_settings(),
            _eval_recorder(door),
            tooling_caller(user_id=USER_ID, paid_overage_approved=False),
        )
    assert raised.value.limit is AiDailyLimit.USER_SHARE
    assert eval_main._limit_exit(raised.value) == 1
    assert AiDailyLimit.USER_SHARE.value in capsys.readouterr().out


class _BoomPipeline:
    """A pipeline double whose conversion fails outside the typed limit path."""

    async def convert(self, *, job: object) -> object:
        raise RuntimeError("boom")


async def test_full_eval_ordinary_crash_stays_a_crash_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom_pipeline(**kwargs: object) -> _BoomPipeline:
        return _BoomPipeline()

    monkeypatch.setattr(eval_main, "build_docx_conversion_pipeline", _boom_pipeline)
    door, _ = _door([])
    report = await eval_main._evaluate(
        _DOCX,
        door,
        _eval_settings(),
        _eval_recorder(door),
        tooling_caller(user_id=USER_ID, paid_overage_approved=False),
    )
    assert report.converted_items == 0
    assert any("boom" in line for line in report.crash)


def test_eval_pool_refusal_through_main_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    async def _refused(*args: object, **kwargs: object) -> list[eval_main._ExamReport]:
        raise AiDailyLimitReached(limit=AiDailyLimit.POOL)

    monkeypatch.setattr(eval_main, "_live", _refused)
    monkeypatch.setattr(
        sys, "argv", ["eval", "--evidence-dir", str(tmp_path), "--user-id", str(USER_ID)]
    )
    assert eval_main.main() == 2
    assert _APPROVAL_TEXT in capsys.readouterr().out


def test_live_labeler_limit_exits_stay_typed(capsys: pytest.CaptureFixture[str]) -> None:
    assert live_main._limit_exit(AiDailyLimitReached(limit=AiDailyLimit.POOL)) == 2
    assert _APPROVAL_TEXT in capsys.readouterr().out
    assert live_main._limit_exit(AiDailyLimitReached(limit=AiDailyLimit.USER_SHARE)) == 1
    assert AiDailyLimit.USER_SHARE.value in capsys.readouterr().out


def test_feasibility_pool_refusal_through_main_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    async def _refused(client: OpenAIClient, args: argparse.Namespace) -> None:
        raise AiDailyLimitReached(limit=AiDailyLimit.POOL)

    monkeypatch.setattr(feasibility_main, "_run", _refused)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "labeling_feasibility",
            "label",
            "--evidence-dir",
            str(tmp_path),
            "--user-id",
            str(USER_ID),
        ],
    )
    assert feasibility_main.main() == 2
    assert _APPROVAL_TEXT in capsys.readouterr().out


def test_feasibility_user_share_refusal_through_main_exits_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    async def _refused(client: OpenAIClient, args: argparse.Namespace) -> None:
        raise AiDailyLimitReached(limit=AiDailyLimit.USER_SHARE)

    monkeypatch.setattr(feasibility_main, "_run", _refused)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "labeling_feasibility",
            "label",
            "--evidence-dir",
            str(tmp_path),
            "--user-id",
            str(USER_ID),
        ],
    )
    assert feasibility_main.main() == 1
    assert AiDailyLimit.USER_SHARE.value in capsys.readouterr().out
