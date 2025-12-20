from __future__ import annotations

from pydantic import JsonValue
from starlette.datastructures import FormData

from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.scripting.ui.contract_v2 import (
    UiActionFieldKind,
    UiEnumField,
    UiFormAction,
    UiMultiEnumField,
)


def parse_action_input(*, action: UiFormAction, form: FormData) -> dict[str, JsonValue]:
    """Parse a submitted HTML form into StartActionCommand.input.

    The schema source of truth is the stored UiFormAction (from ui_payload.next_actions).
    """

    parsed: dict[str, JsonValue] = {}
    for field in action.fields:
        name = field.name

        if field.kind in {UiActionFieldKind.STRING, UiActionFieldKind.TEXT}:
            raw = form.get(name)
            if raw is None:
                continue
            parsed[name] = str(raw)
            continue

        if field.kind is UiActionFieldKind.INTEGER:
            raw = form.get(name)
            if raw is None or str(raw).strip() == "":
                continue
            try:
                parsed[name] = int(str(raw))
            except ValueError as exc:
                raise validation_error(
                    "Invalid integer",
                    details={"field": name, "value": str(raw)},
                ) from exc
            continue

        if field.kind is UiActionFieldKind.NUMBER:
            raw = form.get(name)
            if raw is None or str(raw).strip() == "":
                continue
            try:
                parsed[name] = float(str(raw))
            except ValueError as exc:
                raise validation_error(
                    "Invalid number",
                    details={"field": name, "value": str(raw)},
                ) from exc
            continue

        if field.kind is UiActionFieldKind.BOOLEAN:
            parsed[name] = form.get(name) is not None
            continue

        if field.kind is UiActionFieldKind.ENUM:
            raw = form.get(name)
            if raw is None:
                continue
            selected = str(raw)
            if selected == "":
                continue

            if not isinstance(field, UiEnumField):
                raise validation_error("Invalid enum field schema", details={"field": name})

            allowed = {opt.value for opt in field.options}
            if selected not in allowed:
                raise validation_error(
                    "Invalid enum option",
                    details={"field": name, "value": selected},
                )
            parsed[name] = selected
            continue

        if field.kind is UiActionFieldKind.MULTI_ENUM:
            if not isinstance(field, UiMultiEnumField):
                raise validation_error("Invalid multi_enum field schema", details={"field": name})

            selected_values = [str(v) for v in form.getlist(name) if str(v)]
            allowed = {opt.value for opt in field.options}
            unknown = sorted({v for v in selected_values if v not in allowed})
            if unknown:
                raise validation_error(
                    "Invalid multi_enum option(s)",
                    details={"field": name, "values": unknown},
                )
            selected_json_values: list[JsonValue] = [value for value in selected_values]
            parsed[name] = selected_json_values
            continue

        raise validation_error(
            "Unsupported action field kind",
            details={"field": name, "kind": str(field.kind)},
        )

    return parsed
