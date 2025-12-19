from __future__ import annotations

from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.scripting.ui import contract_v2
from skriptoteket.domain.scripting.ui.policy import UiPolicy

from ._stats import _NormalizationStats


def _count_duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _normalize_actions(
    raw_actions: list[contract_v2.UiFormAction],
    backend_actions: list[contract_v2.UiFormAction],
    *,
    policy: UiPolicy,
    stats: _NormalizationStats,
) -> list[contract_v2.UiFormAction]:
    raw_ids = [action.action_id for action in raw_actions]
    backend_ids = [action.action_id for action in backend_actions]

    raw_duplicates = _count_duplicates(raw_ids)
    if raw_duplicates:
        raise validation_error(
            "Duplicate action_id in tool-provided next_actions",
            details={"duplicates": sorted(raw_duplicates)},
        )

    backend_duplicates = _count_duplicates(backend_ids)
    if backend_duplicates:
        raise validation_error(
            "Duplicate action_id in backend-injected actions",
            details={"duplicates": sorted(backend_duplicates)},
        )

    conflicts = set(raw_ids) & set(backend_ids)
    if conflicts:
        raise validation_error(
            "Action IDs must be unique across tool and backend actions",
            details={"conflicts": sorted(conflicts)},
        )

    combined = sorted(raw_actions, key=lambda action: action.action_id) + sorted(
        backend_actions, key=lambda action: action.action_id
    )

    normalized: list[contract_v2.UiFormAction] = []
    for action in combined:
        fields: list[contract_v2.UiActionField] = []
        for field_item in action.fields:
            if field_item.kind not in policy.allowed_action_field_kinds:
                stats.fields_dropped_disallowed[field_item.kind] = (
                    stats.fields_dropped_disallowed.get(field_item.kind, 0) + 1
                )
                continue

            if isinstance(field_item, contract_v2.UiEnumField):
                if len(field_item.options) > policy.caps.enum_max_options:
                    stats.enum_options_truncated += 1
                    field_item = field_item.model_copy(
                        update={"options": field_item.options[: policy.caps.enum_max_options]}
                    )

            if isinstance(field_item, contract_v2.UiMultiEnumField):
                if len(field_item.options) > policy.caps.multi_enum_max_options:
                    stats.multi_enum_options_truncated += 1
                    field_item = field_item.model_copy(
                        update={"options": field_item.options[: policy.caps.multi_enum_max_options]}
                    )

            fields.append(field_item)

        if len(fields) > policy.caps.max_fields_per_action:
            stats.fields_dropped_due_to_max_fields += (
                len(fields) - policy.caps.max_fields_per_action
            )
            fields = fields[: policy.caps.max_fields_per_action]

        normalized.append(action.model_copy(update={"fields": fields}))

    if len(normalized) > policy.caps.max_next_actions:
        stats.actions_dropped_due_to_max_next_actions += (
            len(normalized) - policy.caps.max_next_actions
        )
        normalized = normalized[: policy.caps.max_next_actions]

    return normalized

