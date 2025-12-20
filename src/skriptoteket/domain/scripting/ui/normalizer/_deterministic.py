from __future__ import annotations

from pydantic import JsonValue

from skriptoteket.domain.scripting.ui import contract_v2
from skriptoteket.domain.scripting.ui.normalization import UiNormalizationResult
from skriptoteket.domain.scripting.ui.policy import UiPolicy

from ._actions import _normalize_actions
from ._json_canonical import _canonicalize_json_value
from ._notices import (
    _SYSTEM_NOTICE_PREFIX,
    _build_system_notices,
    _enforce_ui_payload_budgets,
)
from ._outputs import _normalize_outputs
from ._state import _enforce_state_budget
from ._stats import _NormalizationStats


class DeterministicUiPayloadNormalizer:
    def normalize(
        self,
        *,
        raw_result: contract_v2.ToolUiContractV2Result,
        backend_actions: list[contract_v2.UiFormAction],
        policy: UiPolicy,
    ) -> UiNormalizationResult:
        stats = _NormalizationStats()

        raw_state = raw_result.state or {}
        state_canonical: dict[str, JsonValue] = {}
        for key in sorted(raw_state.keys()):
            canonical, truncated = _canonicalize_json_value(
                raw_state[key],
                max_depth=policy.caps.json_max_depth,
                max_keys=policy.caps.json_max_keys,
                max_array_len=policy.caps.json_max_array_len,
            )
            state_canonical[key] = canonical
            stats.state_truncated_to_json_caps = stats.state_truncated_to_json_caps or truncated

        state_normalized, state_keys_dropped = _enforce_state_budget(
            state_canonical,
            max_bytes=policy.budgets.state_max_bytes,
        )
        stats.state_keys_dropped = state_keys_dropped

        tool_outputs = _normalize_outputs(raw_result.outputs, policy=policy, stats=stats)
        actions = _normalize_actions(
            raw_result.next_actions,
            backend_actions,
            policy=policy,
            stats=stats,
        )

        system_notices: list[contract_v2.UiNoticeOutput] = []

        for _ in range(5):
            system_notices = _build_system_notices(policy=policy, stats=stats)

            max_outputs = policy.caps.max_outputs
            if max_outputs >= 0:
                reserved = len(system_notices)
                if reserved >= max_outputs:
                    stats.outputs_dropped_due_to_max_outputs += len(tool_outputs)
                    tool_outputs = []
                    system_notices = system_notices[:max_outputs]
                else:
                    allowed_tool_outputs = max_outputs - reserved
                    if len(tool_outputs) > allowed_tool_outputs:
                        stats.outputs_dropped_due_to_max_outputs += (
                            len(tool_outputs) - allowed_tool_outputs
                        )
                        tool_outputs = tool_outputs[:allowed_tool_outputs]

            tool_outputs, system_notices, actions = _enforce_ui_payload_budgets(
                tool_outputs,
                system_notices,
                actions,
                policy=policy,
                stats=stats,
            )

            needs_output_cap_notice = stats.outputs_dropped_due_to_max_outputs > 0
            has_output_cap_notice = any(
                notice.message.startswith(f"{_SYSTEM_NOTICE_PREFIX}Output list capped")
                for notice in system_notices
            )
            needs_budget_notice = stats.ui_payload_budget_notice_added
            has_budget_notice = any(
                notice.message.startswith(f"{_SYSTEM_NOTICE_PREFIX}ui_payload exceeded")
                for notice in system_notices
            )
            if (not needs_output_cap_notice or has_output_cap_notice) and (
                not needs_budget_notice or has_budget_notice
            ):
                break

        ui_payload = contract_v2.UiPayloadV2(
            outputs=[*tool_outputs, *system_notices],
            next_actions=actions,
        )
        return UiNormalizationResult(ui_payload=ui_payload, state=state_normalized)
