from __future__ import annotations

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.models import RunContext, RunStatus, VersionState

_VERSION_STATE_LABELS: dict[str, str] = {
    VersionState.DRAFT.value: "Utkast",
    VersionState.IN_REVIEW.value: "Granskning",
    VersionState.ACTIVE.value: "Publicerad",
    VersionState.ARCHIVED.value: "Arkiverad",
}

_RUN_STATUS_LABELS: dict[str, str] = {
    RunStatus.RUNNING.value: "Pågår",
    RunStatus.SUCCEEDED.value: "Lyckades",
    RunStatus.FAILED.value: "Misslyckades",
    RunStatus.TIMED_OUT.value: "Tidsgräns",
}

_RUN_CONTEXT_LABELS: dict[str, str] = {
    RunContext.SANDBOX.value: "Testläge",
    RunContext.PRODUCTION.value: "Produktion",
}


def version_state_label(state: VersionState | str) -> str:
    key = state.value if isinstance(state, VersionState) else str(state)
    return _VERSION_STATE_LABELS.get(key, key)


def run_status_label(status: RunStatus | str) -> str:
    key = status.value if isinstance(status, RunStatus) else str(status)
    return _RUN_STATUS_LABELS.get(key, key)


def run_context_label(context: RunContext | str) -> str:
    key = context.value if isinstance(context, RunContext) else str(context)
    return _RUN_CONTEXT_LABELS.get(key, key)


def ui_error_message(exc: DomainError) -> str:
    if exc.code is ErrorCode.FORBIDDEN:
        return "Du saknar behörighet för detta."

    if exc.code is ErrorCode.NOT_FOUND:
        resource = str(exc.details.get("resource", ""))
        if resource == "Tool":
            return "Verktyget hittades inte."
        if resource == "ToolVersion":
            return "Versionen hittades inte."
        if resource == "ToolRun":
            return "Körningen hittades inte."
        if resource in {"Artifact", "ArtifactFile"}:
            return "Filen hittades inte."
        return "Hittades inte."

    if exc.code is ErrorCode.CONFLICT:
        if "current_head_version_id" in exc.details:
            return "Utkastet har ändrats sedan du öppnade sidan. Ladda om och försök igen."
        return "Det går inte att utföra åtgärden just nu (konflikt)."

    if exc.code is ErrorCode.VALIDATION_ERROR:
        if "expected_parent_version_id" in exc.details:
            return "Versionen stämmer inte längre. Ladda om och försök igen."
        if exc.message == "Title is required":
            return "Titel krävs."
        if exc.message == "Title must be 255 characters or less":
            return "Titeln får vara högst 255 tecken."
        return "Ogiltig indata."

    if exc.code is ErrorCode.SERVICE_UNAVAILABLE:
        return "Tjänsten är tillfälligt otillgänglig. Försök igen."

    return "Ett oväntat fel inträffade."

