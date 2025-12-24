from __future__ import annotations

import hashlib
import json

from pydantic import JsonValue

from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.scripting.ui.contract_v2 import (
    UiActionField,
    UiActionFieldKind,
    UiEnumField,
    UiMultiEnumField,
)

type ToolSettingsSchema = list[UiActionField]
type ToolSettingsValues = dict[str, JsonValue]


def normalize_tool_settings_schema(
    *, settings_schema: ToolSettingsSchema | None
) -> ToolSettingsSchema | None:
    if settings_schema is None:
        return None
    if not settings_schema:
        return None

    seen_names: set[str] = set()
    duplicates: set[str] = set()
    for field in settings_schema:
        if field.name in seen_names:
            duplicates.add(field.name)
        seen_names.add(field.name)

    if duplicates:
        raise validation_error(
            "settings_schema contains duplicate field names",
            details={"duplicates": sorted(duplicates)},
        )

    return settings_schema


def compute_settings_schema_hash(*, settings_schema: ToolSettingsSchema) -> str:
    canonical = json.dumps(
        [field.model_dump(mode="json") for field in settings_schema],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_settings_session_context(*, settings_schema: ToolSettingsSchema) -> str:
    return f"settings:{compute_settings_schema_hash(settings_schema=settings_schema)[:32]}"


def normalize_tool_settings_values(
    *,
    settings_schema: ToolSettingsSchema,
    values: ToolSettingsValues,
) -> ToolSettingsValues:
    by_name = {field.name: field for field in settings_schema}
    unknown_keys = sorted([key for key in values.keys() if key not in by_name])
    if unknown_keys:
        raise validation_error(
            "Unknown settings keys",
            details={"unknown_keys": unknown_keys},
        )

    normalized: ToolSettingsValues = {}

    for field in settings_schema:
        if field.name not in values:
            continue
        raw = values[field.name]

        if raw is None:
            continue

        if field.kind in {UiActionFieldKind.STRING, UiActionFieldKind.TEXT}:
            if not isinstance(raw, str):
                raise validation_error(
                    "Invalid settings value (expected string)",
                    details={"field": field.name, "kind": field.kind.value},
                )
            if not raw:
                continue
            normalized[field.name] = raw
            continue

        if field.kind is UiActionFieldKind.INTEGER:
            if isinstance(raw, bool):
                raise validation_error(
                    "Invalid settings value (expected integer)",
                    details={"field": field.name, "kind": field.kind.value},
                )
            if isinstance(raw, int):
                normalized[field.name] = raw
                continue
            if isinstance(raw, str):
                stripped = raw.strip()
                if not stripped:
                    continue
                try:
                    normalized[field.name] = int(stripped)
                except ValueError as exc:
                    raise validation_error(
                        "Invalid settings value (expected integer)",
                        details={"field": field.name, "kind": field.kind.value},
                    ) from exc
                continue
            raise validation_error(
                "Invalid settings value (expected integer)",
                details={"field": field.name, "kind": field.kind.value},
            )

        if field.kind is UiActionFieldKind.NUMBER:
            if isinstance(raw, bool):
                raise validation_error(
                    "Invalid settings value (expected number)",
                    details={"field": field.name, "kind": field.kind.value},
                )
            if isinstance(raw, (int, float)):
                normalized[field.name] = raw
                continue
            if isinstance(raw, str):
                stripped = raw.strip()
                if not stripped:
                    continue
                try:
                    normalized[field.name] = float(stripped)
                except ValueError as exc:
                    raise validation_error(
                        "Invalid settings value (expected number)",
                        details={"field": field.name, "kind": field.kind.value},
                    ) from exc
                continue
            raise validation_error(
                "Invalid settings value (expected number)",
                details={"field": field.name, "kind": field.kind.value},
            )

        if field.kind is UiActionFieldKind.BOOLEAN:
            if isinstance(raw, bool):
                normalized[field.name] = raw
                continue
            if isinstance(raw, str):
                stripped = raw.strip().lower()
                if not stripped:
                    continue
                if stripped in {"true", "1", "yes", "on"}:
                    normalized[field.name] = True
                    continue
                if stripped in {"false", "0", "no", "off"}:
                    normalized[field.name] = False
                    continue
            raise validation_error(
                "Invalid settings value (expected boolean)",
                details={"field": field.name, "kind": field.kind.value},
            )

        if field.kind is UiActionFieldKind.ENUM:
            if not isinstance(raw, str):
                raise validation_error(
                    "Invalid settings value (expected enum value)",
                    details={"field": field.name, "kind": field.kind.value},
                )
            stripped = raw.strip()
            if not stripped:
                continue
            if not isinstance(field, UiEnumField):
                raise validation_error(
                    "Invalid settings schema (enum field mismatch)",
                    details={"field": field.name, "kind": field.kind.value},
                )
            options = {opt.value for opt in field.options}
            if stripped not in options:
                raise validation_error(
                    "Invalid settings value (unknown enum option)",
                    details={"field": field.name, "kind": field.kind.value},
                )
            normalized[field.name] = stripped
            continue

        if field.kind is UiActionFieldKind.MULTI_ENUM:
            if not isinstance(raw, list):
                raise validation_error(
                    "Invalid settings value (expected list of enum values)",
                    details={"field": field.name, "kind": field.kind.value},
                )

            if not isinstance(field, UiMultiEnumField):
                raise validation_error(
                    "Invalid settings schema (multi_enum field mismatch)",
                    details={"field": field.name, "kind": field.kind.value},
                )
            options = {opt.value for opt in field.options}
            seen: set[str] = set()
            selected: list[JsonValue] = []
            for item in raw:
                if not isinstance(item, str):
                    raise validation_error(
                        "Invalid settings value (expected list of enum values)",
                        details={"field": field.name, "kind": field.kind.value},
                    )
                stripped = item.strip()
                if not stripped:
                    raise validation_error(
                        "Invalid settings value (blank option)",
                        details={"field": field.name, "kind": field.kind.value},
                    )
                if stripped not in options:
                    raise validation_error(
                        "Invalid settings value (unknown enum option)",
                        details={"field": field.name, "kind": field.kind.value},
                    )
                if stripped in seen:
                    continue
                selected.append(stripped)
                seen.add(stripped)

            normalized[field.name] = selected
            continue

        raise validation_error(
            "Invalid settings schema (unknown field kind)",
            details={"field": field.name, "kind": field.kind.value},
        )

    return normalized
