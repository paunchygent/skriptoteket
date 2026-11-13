---
type: reference
id: REF-SKRIPT-GENERAL-scripting-api-contracts-admin-script-editor-user-execution-PART-02
title: Scripting API Contracts - Admin Script Editor & User Execution — part 02
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-scripting-api-contracts-admin-script-editor-user-execution
part: 2
---

### Source: 4. Pydantic DTO Models (Python)

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Literal

VersionState = Literal["draft", "in_review", "active", "archived"]
RunStatus = Literal["running", "succeeded", "failed", "timed_out"]
RunContext = Literal["sandbox", "production"]

class ToolOut(BaseModel):
    id: UUID
    slug: str
    title: str
    summary: Optional[str]
    is_published: bool
    active_version_id: Optional[UUID]

class ToolVersionListItemOut(BaseModel):
    id: UUID
    tool_id: UUID
    version_number: int
    state: VersionState
    entrypoint: str
    content_hash: str
    derived_from_version_id: Optional[UUID]
    created_by: UUID
    created_at: datetime
    submitted_for_review_by: Optional[UUID] = None
    submitted_for_review_at: Optional[datetime] = None
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    published_by: Optional[UUID] = None
    published_at: Optional[datetime] = None
    change_summary: Optional[str] = None

class ToolVersionOut(ToolVersionListItemOut):
    source_code: str
    review_note: Optional[str] = None

class CreateDraftIn(BaseModel):
    derived_from_version_id: Optional[UUID] = None
    entrypoint: str = "run_tool"
    source_code: str
    change_summary: Optional[str] = None

class SaveDraftIn(BaseModel):
    entrypoint: str = "run_tool"
    source_code: str
    change_summary: Optional[str] = None
    expected_parent_version_id: UUID

class SubmitReviewIn(BaseModel):
    review_note: Optional[str] = None

class RequestChangesIn(BaseModel):
    message: Optional[str] = None

class PublishIn(BaseModel):
    change_summary: Optional[str] = None

class RollbackIn(BaseModel):
    from_version_id: UUID
    change_summary: Optional[str] = None

class RunSandboxOptionsIn(BaseModel):
    timeout_s: int = 60
    memory: str = "1024m"
    cpus: str = "1"
    network: str = "none"

class ArtifactOut(BaseModel):
    artifact_id: str
    path: str
    bytes: int
    download_url: str

class ToolRunOut(BaseModel):
    id: UUID
    tool_id: UUID
    version_id: UUID
    context: RunContext
    requested_by: UUID
    status: RunStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    input_filename: str
    input_size_bytes: int
    html_output: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error_summary: Optional[str] = None
    artifacts: list[ArtifactOut] = Field(default_factory=list)

class PublishResultOut(BaseModel):
    tool_id: UUID
    previous_active_version_id: Optional[UUID]
    new_active_version_id: UUID
    archived_version_ids: list[UUID] = Field(default_factory=list)

class RollbackResultOut(BaseModel):
    tool_id: UUID
    previous_active_version_id: UUID
    new_active_version_id: UUID
```

## Decisions And Interpretation

The source contains no separate decision ledger; interpretation remains bounded by the recorded source material.
