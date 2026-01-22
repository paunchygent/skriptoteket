import structlog

from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result, UiFormAction
from skriptoteket.domain.scripting.ui.normalization import UiNormalizationResult
from skriptoteket.domain.scripting.ui.policy import UiPolicy
from skriptoteket.protocols.scripting_ui import UiPayloadNormalizerProtocol

logger = structlog.get_logger(__name__)


def normalize_ui_payload(
    *,
    ui_normalizer: UiPayloadNormalizerProtocol,
    raw_result: ToolUiContractV2Result,
    backend_actions: list[UiFormAction],
    policy: UiPolicy,
    run_id,
) -> UiNormalizationResult:
    try:
        return ui_normalizer.normalize(
            raw_result=raw_result,
            backend_actions=backend_actions,
            policy=policy,
        )
    except DomainError:
        logger.exception(
            "UI payload normalization failed",
            run_id=str(run_id),
        )
        return ui_normalizer.normalize(
            raw_result=ToolUiContractV2Result(
                status="failed",
                error_summary="Execution failed (ui_payload normalization error).",
                outputs=[],
                next_actions=[],
                state=None,
                artifacts=[],
            ),
            backend_actions=backend_actions,
            policy=policy,
        )
