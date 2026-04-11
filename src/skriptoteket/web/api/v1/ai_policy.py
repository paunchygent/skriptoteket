"""AI policy response helpers for SPA-facing app APIs.

Purpose:
    Derive Skriptoteket runtime AI capability policy from local configuration
    without tying it to browser-auth route ownership.

Relationships:
    - Reused by auth ceremony responses while those routes still exist.
    - Used by the app-local profile continuation endpoint added for the
      HuleEdu shared-session bootstrap cutover.
"""

from pydantic import BaseModel, ConfigDict

from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.provider_sets import is_remote_llm_endpoint


class AiPolicyResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    remote_providers_enabled: bool
    completion_external_available: bool
    completion_local_available: bool


def build_ai_policy(settings: Settings) -> AiPolicyResponse:
    completion_candidates = [
        (settings.LLM_COMPLETION_BASE_URL.strip(), settings.LLM_COMPLETION_MODEL.strip()),
        (
            settings.LLM_COMPLETION_FALLBACK_BASE_URL.strip(),
            settings.LLM_COMPLETION_FALLBACK_MODEL.strip(),
        ),
    ]
    configured = [(url, model) for url, model in completion_candidates if url and model]
    completion_external_available = any(is_remote_llm_endpoint(url) for url, _ in configured)
    completion_local_available = any(not is_remote_llm_endpoint(url) for url, _ in configured)
    return AiPolicyResponse(
        remote_providers_enabled=settings.AI_REMOTE_PROVIDERS_ENABLED,
        completion_external_available=completion_external_available,
        completion_local_available=completion_local_available,
    )
