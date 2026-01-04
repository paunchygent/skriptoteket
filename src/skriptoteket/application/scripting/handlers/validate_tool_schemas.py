from __future__ import annotations

from typing import Any

from pydantic import JsonValue as PydanticJsonValue
from pydantic import TypeAdapter, ValidationError

from skriptoteket.application.scripting.commands import (
    SchemaName,
    SchemaValidationIssue,
    ValidateToolSchemasCommand,
    ValidateToolSchemasResult,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.tool_inputs import (
    ToolInputField,
    ToolInputSchema,
    normalize_tool_input_schema,
    validate_input_schema_upload_limits,
)
from skriptoteket.domain.scripting.tool_settings import (
    ToolSettingsSchema,
    normalize_tool_settings_schema,
)
from skriptoteket.domain.scripting.ui.contract_v2 import UiActionField
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol, ToolRepositoryProtocol
from skriptoteket.protocols.scripting import ValidateToolSchemasHandlerProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


def _escape_json_pointer_segment(segment: str) -> str:
    return segment.replace("~", "~0").replace("/", "~1")


def _loc_to_path(loc: tuple[object, ...] | list[object] | None) -> str | None:
    if not loc:
        return None

    parts_source = list(loc)

    # Pydantic discriminated unions include the discriminator tag in loc, e.g. [0, "file", "max"].
    # For editor UX we prefer a JSON Pointer-ish path that matches the actual JSON structure.
    if (
        len(parts_source) >= 3
        and isinstance(parts_source[0], int)
        and isinstance(parts_source[1], str)
        and parts_source[1]
        in {"string", "text", "integer", "number", "boolean", "enum", "multi_enum", "file"}
    ):
        parts_source.pop(1)

    parts: list[str] = []
    for item in parts_source:
        if item in {"__root__", "$"}:
            continue
        if isinstance(item, int):
            parts.append(str(item))
            continue
        if isinstance(item, str):
            parts.append(_escape_json_pointer_segment(item))
            continue
        parts.append(_escape_json_pointer_segment(str(item)))

    if not parts:
        return None
    return "/" + "/".join(parts)


def _issues_from_validation_error(
    *,
    schema: SchemaName,
    exc: ValidationError,
) -> list[SchemaValidationIssue]:
    issues: list[SchemaValidationIssue] = []
    for error in exc.errors():
        loc = error.get("loc") or ()
        message = error.get("msg") or "Invalid schema"
        issues.append(
            SchemaValidationIssue(
                schema=schema,
                path=_loc_to_path(loc),
                message=message,
                details={"type": error.get("type", "validation_error")},
            )
        )
    return issues


def _issue_from_domain_validation_error(
    *,
    schema: SchemaName,
    exc: DomainError,
) -> SchemaValidationIssue:
    details = exc.details or None
    return SchemaValidationIssue(
        schema=schema,
        path=None,
        message=exc.message,
        details=details,  # type: ignore[arg-type]
    )


def _issues_from_upload_limit_error(
    *,
    schema: SchemaName,
    exc: DomainError,
) -> list[SchemaValidationIssue]:
    details: dict[str, Any] = exc.details or {}
    index = details.get("index")
    field_name = details.get("field")
    upload_max_files = details.get("upload_max_files")
    violations = details.get("violations") or []

    issues: list[SchemaValidationIssue] = []
    for key in violations:
        if key not in {"min", "max"}:
            continue
        path = None
        if isinstance(index, int):
            path = f"/{index}/{key}"
        value = details.get(key)
        message = (
            f"File field '{field_name}' has {key}={value}, but server upload limit is "
            f"{upload_max_files}."
        )
        issues.append(
            SchemaValidationIssue(
                schema=schema,
                path=path,
                message=message,
                details={
                    "field": str(field_name) if field_name is not None else None,
                    "key": key,
                    "value": value,
                    "upload_max_files": upload_max_files,
                },
            )
        )
    return issues or [_issue_from_domain_validation_error(schema=schema, exc=exc)]


def _validate_settings_schema(
    *,
    raw: PydanticJsonValue | None,
    issues: list[SchemaValidationIssue],
) -> ToolSettingsSchema | None:
    if raw is None:
        return None

    if not isinstance(raw, list):
        issues.append(
            SchemaValidationIssue(
                schema=SchemaName.SETTINGS_SCHEMA,
                path=None,
                message="settings_schema must be an array or null",
            )
        )
        return None

    try:
        parsed = TypeAdapter(list[UiActionField]).validate_python(raw)
    except ValidationError as exc:
        issues.extend(_issues_from_validation_error(schema=SchemaName.SETTINGS_SCHEMA, exc=exc))
        return None

    try:
        return normalize_tool_settings_schema(settings_schema=parsed)
    except DomainError as exc:
        if exc.code is not ErrorCode.VALIDATION_ERROR:
            raise
        issues.append(
            _issue_from_domain_validation_error(schema=SchemaName.SETTINGS_SCHEMA, exc=exc)
        )
        return None


def _validate_input_schema(
    *,
    raw: PydanticJsonValue | None,
    upload_max_files: int,
    issues: list[SchemaValidationIssue],
) -> ToolInputSchema:
    if raw is None:
        issues.append(
            SchemaValidationIssue(
                schema=SchemaName.INPUT_SCHEMA,
                path=None,
                message="input_schema is required and must be an array",
            )
        )
        return []

    if not isinstance(raw, list):
        issues.append(
            SchemaValidationIssue(
                schema=SchemaName.INPUT_SCHEMA,
                path=None,
                message="input_schema must be an array",
            )
        )
        return []

    try:
        parsed = TypeAdapter(list[ToolInputField]).validate_python(raw)
    except ValidationError as exc:
        issues.extend(_issues_from_validation_error(schema=SchemaName.INPUT_SCHEMA, exc=exc))
        return []

    try:
        normalized = normalize_tool_input_schema(input_schema=parsed)
    except DomainError as exc:
        if exc.code is not ErrorCode.VALIDATION_ERROR:
            raise
        issues.append(_issue_from_domain_validation_error(schema=SchemaName.INPUT_SCHEMA, exc=exc))
        return []

    try:
        validate_input_schema_upload_limits(
            input_schema=normalized,
            upload_max_files=upload_max_files,
        )
    except DomainError as exc:
        if exc.code is not ErrorCode.VALIDATION_ERROR:
            raise
        issues.extend(_issues_from_upload_limit_error(schema=SchemaName.INPUT_SCHEMA, exc=exc))

    return normalized


class ValidateToolSchemasHandler(ValidateToolSchemasHandlerProtocol):
    def __init__(
        self,
        *,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
    ) -> None:
        self._settings = settings
        self._uow = uow
        self._tools = tools
        self._maintainers = maintainers

    async def handle(
        self,
        *,
        actor: User,
        command: ValidateToolSchemasCommand,
    ) -> ValidateToolSchemasResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        async with self._uow:
            tool = await self._tools.get_by_id(tool_id=command.tool_id)
            if tool is None:
                raise not_found("Tool", str(command.tool_id))

            if actor.role is Role.CONTRIBUTOR:
                is_tool_maintainer = await self._maintainers.is_maintainer(
                    tool_id=tool.id,
                    user_id=actor.id,
                )
                if not is_tool_maintainer:
                    raise DomainError(
                        code=ErrorCode.FORBIDDEN,
                        message="Insufficient permissions",
                        details={"tool_id": str(tool.id)},
                    )

        issues: list[SchemaValidationIssue] = []

        _validate_settings_schema(raw=command.settings_schema, issues=issues)
        _validate_input_schema(
            raw=command.input_schema,
            upload_max_files=self._settings.UPLOAD_MAX_FILES,
            issues=issues,
        )

        return ValidateToolSchemasResult(
            valid=not issues,
            issues=issues,
        )
