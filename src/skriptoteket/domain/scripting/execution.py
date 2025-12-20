from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.models import RunStatus
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result


class ToolExecutionResult(BaseModel):
    """Final execution result produced by an execution provider (not a DB model)."""

    model_config = ConfigDict(frozen=True)

    status: RunStatus
    stdout: str
    stderr: str
    ui_result: ToolUiContractV2Result
    artifacts_manifest: ArtifactsManifest
