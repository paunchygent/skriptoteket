---
type: reference
id: REF-scripting-api-contracts
title: "Scripting API Contracts - Admin Script Editor & User Execution"
status: active
owners: "agents"
created: 2025-12-14
topic: "scripting"
---

## Overview

This document defines the API contracts for the Admin Script Editor and User Execution features (EPIC-04).

Related documents:

- Design spec: REF-dynamic-tool-scripts
- ADRs: ADR-0012, ADR-0013, ADR-0014, ADR-0015, ADR-0016
- Epic: EPIC-04

---

## 0. Standard Response Shapes

### 0.1 Error Response (all endpoints)

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Only admin can publish.",
    "details": {
      "version_id": "..."
    }
  }
}
```

**Common error codes:**

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `FORBIDDEN` | 403 | User lacks permission |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `CONFLICT` | 409 | State conflict (e.g. `STATE_CONFLICT`, `ACTIVE_VERSION_CONSTRAINT`) |
| `SERVICE_UNAVAILABLE` | 503 | Execution service is temporarily unavailable (e.g. runner at capacity) |

Notes:

- Script execution failures/timeouts are represented via `ToolRunOut.status` (`failed` / `timed_out`) and are typically
  returned with HTTP 200 for “execution completed with an outcome”.
- `DomainError` error codes are reserved for control-plane failures (permission, not found, invalid state, etc.).

### 0.2 ToolOut DTO

```json
{
  "id": "uuid",
  "slug": "string",
  "title": "string",
  "summary": "string|null",
  "is_published": true,
  "active_version_id": "uuid|null"
}
```

### 0.3 ToolVersionListItemOut DTO

```json
{
  "id": "uuid",
  "tool_id": "uuid",
  "version_number": 12,
  "state": "draft|in_review|active|archived",
  "entrypoint": "run_tool",
  "content_hash": "sha256-hex",
  "derived_from_version_id": "uuid|null",
  "created_by": "uuid",
  "created_at": "2025-12-14T12:03:00Z",
  "submitted_for_review_by": "uuid|null",
  "submitted_for_review_at": "2025-12-14T12:10:00Z|null",
  "reviewed_by": "uuid|null",
  "reviewed_at": "2025-12-14T12:10:00Z|null",
  "published_by": "uuid|null",
  "published_at": "2025-12-14T12:20:00Z|null",
  "change_summary": "string|null"
}
```

### 0.4 ToolVersionOut DTO

Used when opening a version (includes `source_code`):

```json
{
  "id": "uuid",
  "tool_id": "uuid",
  "version_number": 12,
  "state": "draft",
  "entrypoint": "run_tool",
  "source_code": "def run_tool(...):\n    ...\n",
  "content_hash": "sha256-hex",
  "derived_from_version_id": "uuid|null",
  "created_by": "uuid",
  "created_at": "2025-12-14T12:03:00Z",
  "submitted_for_review_by": "uuid|null",
  "submitted_for_review_at": "2025-12-14T12:10:00Z|null",
  "reviewed_by": "uuid|null",
  "reviewed_at": "2025-12-14T12:10:00Z|null",
  "published_by": "uuid|null",
  "published_at": "2025-12-14T12:20:00Z|null",
  "change_summary": "string|null",
  "review_note": "string|null"
}
```

### 0.5 ArtifactOut DTO

```json
{
  "artifact_id": "string",
  "path": "output/report.pdf",
  "bytes": 120000,
  "download_url": "/admin/tool-runs/<run_id>/artifacts/<artifact_id>"
}
```

### 0.6 ToolRunOut DTO

```json
{
  "id": "uuid",
  "tool_id": "uuid",
  "version_id": "uuid",
  "context": "sandbox|production",
  "requested_by": "uuid",
  "status": "running|succeeded|failed|timed_out",
  "started_at": "2025-12-14T12:03:00Z",
  "finished_at": "2025-12-14T12:03:09Z|null",
  "input_filename": "file.csv",
  "input_size_bytes": 12345,
  "html_output": "<p>...</p>",
  "stdout": "...",
  "stderr": "...",
  "error_summary": "...|null",
  "artifacts": [
    {
      "artifact_id": "output_report_pdf",
      "path": "output/report.pdf",
      "bytes": 120000,
      "download_url": "/admin/tool-runs/<run_id>/artifacts/output_report_pdf"
    }
  ]
}
```

---

## 1. User Endpoints (Production Run)

### 1.1 Show Run Page

```http
GET /tools/{slug}/run
Auth: User
```

**Response:** HTML page with upload form.

### 1.2 Execute Tool

```http
POST /tools/{slug}/run
Auth: User
Content-Type: multipart/form-data
```

**Form fields:**

- `file`: uploaded file (required)

**Response 200:** HTML result page (rendered from `html_output`). Logs are hidden.

**Response 404:** Tool does not exist or is not published.
Also return 404 if the tool is published but `active_version_id` is missing/invalid/non-ACTIVE (defense in depth).

### 1.3 View Past Run

```http
GET /my-runs/{run_id}
Auth: User (own runs only)
```

**Response 200:** HTML result page (same rendering as the immediate POST result).

**Response 404:** Run does not exist or does not belong to the current user.

---

## 2. Admin Editor Endpoints

Note (v0.1 UI): Skriptoteket uses a server-rendered admin UI + HTMX. The `/admin/...` endpoints are implemented as
HTML pages and HTML fragments (see `src/skriptoteket/web/pages/admin_scripting.py`). The JSON DTOs below document the
logical shapes and are intended for a future `/api/v1` surface.

### 2.1 Load Tool Metadata

```http
GET /admin/tools/{tool_id}
Auth: Admin, Superuser (optional: Contributor if viewing assigned tools)
```

**Response 200:**

```json
{
  "tool": {
    "id": "...",
    "slug": "example-tool",
    "title": "Example Tool",
    "summary": "Does something",
    "is_published": true,
    "active_version_id": "..."
  }
}
```

### 2.2 Version History

```http
GET /admin/tools/{tool_id}/versions?state=draft,in_review,active,archived&limit=50
Auth: Contributor (restricted to own), Admin, Superuser
```

**Response 200:**

```json
{
  "tool_id": "...",
  "versions": [ "...ToolVersionListItemOut..." ]
}
```

### 2.3 Open Version (Load Source Code)

```http
GET /admin/tool-versions/{version_id}
Auth: Contributor (own drafts only), Admin, Superuser
```

**Response 200:** `ToolVersionOut`

### 2.4 Create New Draft

```http
POST /admin/tools/{tool_id}/versions
Auth: Contributor, Admin, Superuser
```

**Request:** `CreateDraftIn`
**Response 201:** `ToolVersionListItemOut`

### 2.5 Save Draft Snapshot

```http
POST /admin/tool-versions/{version_id}/save
Auth: Contributor (own drafts only), Admin, Superuser
```

**Request:** `SaveDraftIn`
**Response 201:** `ToolVersionListItemOut` (new version)

### 2.6 Submit for Review

```http
POST /admin/tool-versions/{version_id}/submit-review
Auth: Contributor (own drafts), Admin, Superuser
```

**Request:** `SubmitReviewIn`
**Response 200:** `ToolVersionListItemOut` (state=in_review, sets `submitted_for_review_by` + `submitted_for_review_at`)

### 2.7 Request Changes (Admin & Superuser)

```http
POST /admin/tool-versions/{version_id}/request-changes
Auth: Admin, Superuser
Precondition: version is in_review
```

**Request:** `RequestChangesIn`

**Response 200:**

`ToolVersionListItemOut` (new version, state=draft)

**Server behavior (append-only):**

1. Archive the reviewed IN_REVIEW version (it is consumed by the request-changes action).
2. Create a NEW DRAFT version derived from the reviewed version (copy source_code/entrypoint).
   - `created_by_user_id` is set to the original author (`reviewed_version.created_by_user_id`) to preserve contributor
     ownership rules.
   - The reviewer message is stored in `change_summary` on the new draft (until a dedicated reviewer-note field
     exists).

### 2.8 Publish (Admin & Superuser)

```http
POST /admin/tool-versions/{version_id}/publish
Auth: Admin, Superuser
Precondition: version is in_review
```

**Request:** `PublishIn`

**Response 200:**

```json
{
  "tool_id": "...",
  "previous_active_version_id": "uuid|null",
  "new_active_version_id": "uuid",
  "archived_version_ids": ["uuid", "uuid"]
}
```

**Server behavior (copy-on-activate):**

1. Archive the current ACTIVE version (if any).
2. Create a NEW ACTIVE version derived from the reviewed IN_REVIEW version (copy source_code/entrypoint).
3. Archive the reviewed IN_REVIEW version (it is consumed by publishing).
4. Update `tools.active_version_id` to the new ACTIVE version.

### 2.9 Rollback (Superuser Only)

```http
POST /admin/tools/{tool_id}/rollback
Auth: Superuser
```

**Request:** `RollbackIn`
**Response 200:** `RollbackResultOut`

---

## 3. Sandbox Run Endpoints

### 3.1 Run Sandbox

```http
POST /admin/tool-versions/{version_id}/run-sandbox
Auth: Contributor (own drafts), Admin, Superuser
```

**Response 200:** `ToolRunOut`

### 3.2 Refresh Run Details

```http
GET /admin/tool-runs/{run_id}
Auth: Admin, Superuser (Contributor for own runs)
```

**Response 200:** `ToolRunOut`

### 3.3 Download Artifact

```http
GET /admin/tool-runs/{run_id}/artifacts/{artifact_id}
Auth: Admin, Superuser (Contributor for own runs)
```

**Response 200:** File stream.

---

## 4. Pydantic DTO Models (Python)

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
