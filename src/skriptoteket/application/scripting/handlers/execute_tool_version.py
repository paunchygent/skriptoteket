from __future__ import annotations

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionCommand,
    ExecuteToolVersionResult,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.execution import ArtifactsManifest, ToolExecutionResult
from skriptoteket.domain.scripting.models import RunStatus, finish_tool_run, start_tool_run
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.runner import ToolRunnerProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


def _format_syntax_error(exc: SyntaxError) -> str:
    parts: list[str] = [f"SyntaxError: {exc.msg}"]

    location_parts: list[str] = []
    if exc.lineno is not None:
        location_parts.append(f"line {exc.lineno}")
    if exc.offset is not None:
        location_parts.append(f"col {exc.offset}")
    if location_parts:
        parts[0] = f"{parts[0]} ({', '.join(location_parts)})"

    if exc.text:
        code_line = exc.text.rstrip("\n")
        parts.append(code_line)
        if exc.offset is not None:
            caret_position = max(exc.offset - 1, 0)
            parts.append(" " * caret_position + "^")

    return "\n".join(parts)


class ExecuteToolVersionHandler(ExecuteToolVersionHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        runs: ToolRunRepositoryProtocol,
        runner: ToolRunnerProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._versions = versions
        self._runs = runs
        self._runner = runner
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        command: ExecuteToolVersionCommand,
    ) -> ExecuteToolVersionResult:
        version = await self._versions.get_by_id(version_id=command.version_id)
        if version is None:
            raise not_found("ToolVersion", str(command.version_id))
        if version.tool_id != command.tool_id:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="ToolVersion does not belong to the specified Tool",
                details={
                    "tool_id": str(command.tool_id),
                    "version_id": str(command.version_id),
                    "version_tool_id": str(version.tool_id),
                },
            )

        now = self._clock.now()
        run_id = self._id_generator.new_uuid()
        run = start_tool_run(
            run_id=run_id,
            tool_id=command.tool_id,
            version_id=command.version_id,
            context=command.context,
            requested_by_user_id=actor.id,
            workdir_path=str(run_id),
            input_filename=command.input_filename,
            input_size_bytes=len(command.input_bytes),
            now=now,
        )

        async with self._uow:
            await self._runs.create(run=run)

        execution_result: ToolExecutionResult | None = None
        domain_error_to_raise: DomainError | None = None

        try:
            compile(version.source_code, "<tool_version>", "exec")
            execution_result = await self._runner.execute(
                run_id=run_id,
                version=version,
                context=command.context,
                input_filename=command.input_filename,
                input_bytes=command.input_bytes,
            )
        except SyntaxError as exc:
            execution_result = ToolExecutionResult(
                status=RunStatus.FAILED,
                stdout="",
                stderr="",
                html_output="",
                error_summary=_format_syntax_error(exc),
                artifacts_manifest=ArtifactsManifest(artifacts=[]),
            )
        except DomainError as exc:
            domain_error_to_raise = exc
        except Exception:  # noqa: BLE001
            domain_error_to_raise = DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Execution failed (internal error).",
            )

        finish_now = self._clock.now()
        if execution_result is None:
            finished = finish_tool_run(
                run=run,
                status=RunStatus.FAILED,
                now=finish_now,
                html_output="",
                stdout="",
                stderr="",
                artifacts_manifest={},
                error_summary=None
                if domain_error_to_raise is None
                else domain_error_to_raise.message,
            )
        else:
            finished = finish_tool_run(
                run=run,
                status=execution_result.status,
                now=finish_now,
                html_output=execution_result.html_output,
                stdout=execution_result.stdout,
                stderr=execution_result.stderr,
                artifacts_manifest=execution_result.artifacts_manifest.model_dump(),
                error_summary=execution_result.error_summary,
            )

        async with self._uow:
            await self._runs.update(run=finished)

        if domain_error_to_raise is not None:
            raise domain_error_to_raise

        return ExecuteToolVersionResult(run=finished)
