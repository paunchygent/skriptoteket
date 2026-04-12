"""Profile-backed AI preference update handler.

Purpose:
    Persist the app-local AI preferences used by editor assistance without
    caching browser-session state.

Relationships:
    - Invoked by `/api/v1/profile/ai-settings`.
    - Read by app-auth dependencies through `UserProfile` after PR-0253.
"""

from __future__ import annotations

from skriptoteket.application.identity.commands import (
    UpdateAiSettingsCommand,
    UpdateAiSettingsResult,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    ProfileRepositoryProtocol,
    UpdateAiSettingsHandlerProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class UpdateAiSettingsHandler(UpdateAiSettingsHandlerProtocol):
    def __init__(
        self,
        *,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._settings = settings
        self._uow = uow
        self._users = users
        self._profiles = profiles
        self._clock = clock

    async def handle(self, command: UpdateAiSettingsCommand) -> UpdateAiSettingsResult:
        async with self._uow:
            user = await self._users.get_by_id(command.user_id)
            if user is None:
                raise not_found("User", str(command.user_id))

            profile = await self._profiles.get_by_user_id(user_id=command.user_id)
            if profile is None:
                raise not_found("UserProfile", str(command.user_id))

            allow_remote_fallback = profile.allow_remote_fallback
            if command.remote_fallback_preference is not None:
                if command.remote_fallback_preference == "allow":
                    if not self._settings.AI_REMOTE_PROVIDERS_ENABLED:
                        raise DomainError(
                            code=ErrorCode.FORBIDDEN,
                            message=(
                                "Systemadministratören tillåter inte externa AI-modeller i den här "
                                "miljön."
                            ),
                        )
                    allow_remote_fallback = True
                elif command.remote_fallback_preference == "deny":
                    allow_remote_fallback = False
                else:
                    allow_remote_fallback = None

            inline_completion_provider = profile.inline_completion_provider
            requested_external_completion = (
                command.inline_completion_provider_preference == "external"
            )
            if command.inline_completion_provider_preference is not None:
                if command.inline_completion_provider_preference == "unset":
                    inline_completion_provider = None
                else:
                    inline_completion_provider = command.inline_completion_provider_preference

            if requested_external_completion and not self._settings.AI_REMOTE_PROVIDERS_ENABLED:
                raise DomainError(
                    code=ErrorCode.FORBIDDEN,
                    message=(
                        "Systemadministratören tillåter inte externa AI-modeller i den här miljön."
                    ),
                )

            if (
                not self._settings.AI_REMOTE_PROVIDERS_ENABLED
                and inline_completion_provider == "external"
            ):
                inline_completion_provider = None

            if allow_remote_fallback is not True and inline_completion_provider == "external":
                if requested_external_completion:
                    raise DomainError(
                        code=ErrorCode.VALIDATION_ERROR,
                        message=(
                            "Aktivera externa AI-API:er i Profil → AI-inställningar innan du "
                            "väljer externa completions."
                        ),
                    )
                inline_completion_provider = None

            now = self._clock.now()
            updated_profile = profile.model_copy(
                update={
                    "allow_remote_fallback": allow_remote_fallback,
                    "inline_completion_provider": inline_completion_provider,
                    "updated_at": now,
                }
            )
            saved_profile = await self._profiles.update(profile=updated_profile)

        return UpdateAiSettingsResult(user=user, profile=saved_profile)
