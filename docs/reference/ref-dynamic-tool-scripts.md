---
type: reference
id: REF-dynamic-tool-scripts
title: "Dynamic Tool Scripts - Design Specification"
status: active
owners: "agents"
created: 2025-12-14
topic: "scripting"
---

## Problem Statement

Publishing new tool logic currently requires repository changes and redeployment. This blocks rapid iteration and prevents on-site admins from implementing approved tools in a single session.

## Goals

- Enable privileged users to author, review, and run Python tool logic without redeploy
- Provide draft execution for verification before publishing
- Ensure exactly one active (user-facing) version per tool
- Maintain immutable, auditable published versions suitable for later export to GitHub

## Non-Goals

- Running untrusted user-uploaded code (users upload data, not code)
- Dynamic package installation (pip) at runtime
- Multi-language runtime support (Python only for now)
- Asynchronous job queue for long-running tasks (may be added later)
- Fixture library for saved test inputs (deferred to future epic)
- Repo-seedad “script bank” som ändrar runtime scripts automatiskt (manuell seed via CLI är OK)

## Related Documents

- Epic: EPIC-04
- ADRs: ADR-0012 (storage), ADR-0013 (execution), ADR-0014 (versioning), ADR-0015 (runner contract), ADR-0016 (concurrency)
- API Contracts: REF-scripting-api-contracts

---

## Lifecycle: Suggestion → Runnable Tool

This feature is designed to work end-to-end with the EPIC-03 governance workflow (suggestions + catalog visibility)
and the EPIC-04 scripting workflow (versioned script code + execution).

### Sequence flow (happy path)

1. **Contributor suggests a tool** (title/description/professions/categories).
2. **Admin reviews suggestion** and **accepts** it, creating a **draft tool** entry (not published, not runnable yet).
3. **Admin opens the script editor** for the draft tool and **creates a ToolVersion in `draft`** (starter template or
   derived from an existing version).
4. **Admin iterates**: each Save creates a new immutable draft snapshot; admin can **run sandbox tests** and inspect
   HTML + logs + artifacts.
5. **Submit for review**: a specific snapshot becomes `in_review` (optionally with `review_note`).
6. **Publish script version** (Admin/Superuser): copy-on-activate creates a NEW `active` version, archives the previous
   active (if any), and archives the reviewed `in_review` snapshot (**publish consumes in_review**).
   - See: [ST-04-04 Governance, audit, and rollback](../backlog/stories/story-04-04-governance-audit-rollback.md)
7. **Publish tool (catalog visibility)** (Admin): sets `tools.is_published=true`, which makes the tool discoverable and
   runnable **only if** `tools.active_version_id` is set (published implies runnable).
   - See: [ST-03-03 Admins publish/depublish tools](../backlog/stories/story-03-03-publish-and-depublish-tools.md)
8. **User runs the tool**: `GET/POST /tools/{slug}/run` executes the ACTIVE version in production context and renders
   the HTML result (logs hidden from end-users).

### Variations

- **Rollback (Superuser)**: create a new ACTIVE version derived from an older archived version. If the tool is
  published, users immediately run the rolled-back ACTIVE version.
  - See: [ST-04-04 Governance, audit, and rollback](../backlog/stories/story-04-04-governance-audit-rollback.md)

---

## Repo-level script bank (seed)

För att ha realistiska “exempelverktyg” i repo:t (med svensk, lärarfokuserad copy) finns en liten script bank under:

- `src/skriptoteket/script_bank/`

Den kan seedas till databasen (skapar verktyg + första ACTIVE versionen, och kan publicera verktyget) via:

- `pdm run seed-script-bank`

Tips:

- Kör med `--dry-run` för att se vad som skulle hända.
- `--sync-metadata` uppdaterar `tools.title`/`tools.summary` för redan existerande verktyg.
- `--sync-code` skapar + publicerar en ny version om ACTIVE skiljer sig från repo-scriptet.

## Domain Model

### New Domain: `scripting`

Separate from `catalog` domain. Catalog owns Tool metadata; scripting owns versions and execution.

### Entities

#### ToolVersion

```text
ToolVersion
  id: UUID
  tool_id: UUID (FK -> tools)
  version_number: int (monotonic per tool)
  state: VersionState (draft | in_review | active | archived)
  source_code: str
  entrypoint: str (default "run_tool")
  content_hash: str (sha256 of "{entrypoint}\\n{source_code}")
  derived_from_version_id: UUID | None
  created_by: UUID
  created_at: datetime
  submitted_for_review_by: UUID | None
  submitted_for_review_at: datetime | None
  reviewed_by: UUID | None
  reviewed_at: datetime | None
  published_by: UUID | None
  published_at: datetime | None
  change_summary: str | None
  review_note: str | None  (new field)
```

Notes:

- `submitted_for_review_*` records the **Draft → InReview** transition (who submitted and when).
- `reviewed_*` is reserved for reviewer actions (e.g. "request changes" / future explicit review events) and is **not**
  used for submission audit.

#### ToolRun

```text
ToolRun
  id: UUID
  tool_id: UUID
  version_id: UUID
  context: RunContext (production | sandbox)
  requested_by: UUID
  status: RunStatus (running | succeeded | failed | timed_out)
  started_at: datetime
  finished_at: datetime | None
  workdir_path: str (relative path/key under artifacts root, e.g. "{run_id}/")
  input_filename: str
  input_size_bytes: int
  html_output: str | None  (Stored in DB)
  stdout: str | None       (Stored in DB)
  stderr: str | None       (Stored in DB)
  artifacts_manifest: dict (References files on disk)
  error_summary: str | None
```

#### Tool (extended)

Add to existing Tool entity:

```text
active_version_id: UUID | None (FK -> tool_versions)
```

### State Machine

```text
[*] --> Draft
Draft --> Draft: Save (creates new Draft version)
Draft --> InReview: Submit for review
InReview --> Draft: Request changes (new Draft derived)
InReview --> Active: Publish (creates new Active, old InReview -> Archived)
Active --> Archived: Superseded by new publish
Archived --> Active: Rollback (publish derived-from archived)
```

### Database Constraints

```sql
-- Exactly one active per tool (partial unique index)
CREATE UNIQUE INDEX ux_tool_versions_one_active_per_tool
ON tool_versions(tool_id)
WHERE state = 'active';

-- Uniqueness + queryable history (monotonic per tool)
ALTER TABLE tool_versions
  ADD CONSTRAINT uq_tool_versions_tool_id_version_number
  UNIQUE (tool_id, version_number);
```

Audit FK policy:

- `created_by`, `submitted_for_review_by`, `reviewed_by`, `published_by`, `requested_by` reference `users(id)` with
  `ON DELETE RESTRICT` to preserve audit history (user deletion is blocked if referenced).

---

## Permission Matrix

### Roles

- **User**: Normal end-user running published tools
- **Contributor**: Can author drafts but cannot publish
- **Admin**: Trusted reviewer/operator (can run drafts, review, **publish**)
- **Superuser**: Governance override (**rollback**) and can also publish

### Tool + Script Governance

| Action | User | Contributor | Admin | Superuser |
|--------|------|-------------|-------|-----------|
| View published tool catalog | Y | Y | Y | Y |
| Create tool metadata | - | - | Y | Y |
| Edit tool metadata | - | - | Y | Y |
| View version list | - | Own only | Y | Y |
| View version source code | - | Own only | Y | Y |
| Create new Draft version | - | Y | Y | Y |
| Save draft snapshot | - | Own only | Y | Y |
| Submit draft -> InReview | - | Own only | Y | Y |
| Move InReview -> Draft | - | - | Y | Y |
| Publish (InReview -> Active) | - | - | **Y** | Y |
| Rollback | - | - | - | Y |

### Execution

| Action | User | Contributor | Admin | Superuser |
|--------|------|-------------|-------|-----------|
| Run Active version (production) | Y | Y | Y | Y |
| Run Draft/InReview in sandbox | - | Own only | Y | Y |
| View own run results | Y | Y | Y | Y |
| View any run results | - | - | Y | Y |

---

## Execution Model

### Script Contract

Every script version must define:

```python
def run_tool(input_dir: str, output_dir: str) -> dict:
    """
    - Discover uploaded files via SKRIPTOTEKET_INPUT_MANIFEST (paths under /work/input)
    - Write any artifacts into output_dir
    - Return a UI contract v2 payload (outputs/next_actions/state)
    """
```

### Runner Wrapper

Stable `_runner.py` (not user-edited) handles:

- Loading script module dynamically
- Invoking entrypoint function
- Collecting artifacts from output_dir
- Writing `result.json` with html/artifacts/error

### Docker Execution (Sibling Containers)

The app container uses the Docker SDK to spawn a sibling runner container.

```bash
docker run --detach \
  --cpus {config.CPU_LIMIT} \
  --memory {config.MEM_LIMIT} \
  --pids-limit 256 \
  --read-only \
  --tmpfs /work:rw,noexec,nosuid,nodev,size=512m \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=256m \
  --network none \
  --user runner \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  {runner_image} \
  python _runner.py
```

I/O is handled via Docker Engine APIs (archive copy via `put_archive` / `get_archive`) or strictly scoped volumes.
No host-path bind mounts are used.

### Sandbox vs Production

| Aspect | Sandbox | Production |
|--------|---------|------------|
| Network | Disabled (`--network none`) | v0.2 defaults to disabled; per-tool enablement deferred |
| Secrets | None injected | v0.2 injects none; per-tool injection deferred |
| Run record context | `sandbox` | `production` |
| Logs Visibility | Visible to author/admin | Hidden from user (error summary only) |

---

## API Surface

### User Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tools/{slug}/run` | Show run form |
| POST | `/tools/{slug}/run` | Run active version, returns result page |
| GET | `/my-runs/{run_id}` | View past run result |

### Admin Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/tools/{tool_id}/versions` | List versions |
| POST | `/admin/tools/{tool_id}/versions` | Create draft (derived from active/latest) |
| POST | `/admin/tool-versions/{version_id}/save` | Save draft snapshot |
| POST | `/admin/tool-versions/{version_id}/submit-review` | Submit for review |
| POST | `/admin/tool-versions/{version_id}/request-changes` | Request changes (in_review → new draft) |
| POST | `/admin/tool-versions/{version_id}/run-sandbox` | Run in sandbox |
| POST | `/admin/tool-versions/{version_id}/publish` | Publish (Admin/Superuser) |
| POST | `/admin/tools/{tool_id}/rollback` | Rollback (Superuser) |

---

## UI Wireframe

### Admin Script Editor Page

```text
+----------------------------------------------------------------------+
| Tool: [Title]  Slug: [slug]  Status: [DRAFT]  Version: v12           |
| Actions: [Save Draft] [Submit for Review] [Request Changes*] [Publish*] [Rollback*] |
+----------------------------------------------------------------------+

+----------------------------------+-----------------------------------+
| Editor (Python)                  | Run (Sandbox)                     |
| +------------------------------+ | Context: [Sandbox]                |
| | def run_tool(...):           | | Input: [Upload File]              |
| |     ...                      | | Limits: 60s | 1 CPU | 1GB         |
| +------------------------------+ | [Run Sandbox]                     |
| Entrypoint: [run_tool]           | Last run: succeeded 12:03         |
+----------------------------------+-----------------------------------+

+----------------------------------+-----------------------------------+
| HTML Preview                     | Logs                              |
| +------------------------------+ | Tabs: [stdout] [stderr]           |
| | (rendered HTML output)       | | +-------------------------------+ |
| +------------------------------+ | | ...log content...             | |
+----------------------------------+-----------------------------------+
```

---

## Operational Constraints

### Dependency Management

- Runner image includes curated set of libs (pandas, openpyxl, pypdf, pillow, etc.)
- New dependency = runner image rebuild (redeploy required)
- Keeps runtime deterministic, avoids pip drift

### Artifact Storage

- **Logs/HTML:** Stored in DB `tool_runs` table.
- **Binaries:** Stored on disk `/var/lib/skriptoteket/artifacts/`.
- **Input retention:** Sandbox input files are retained (short retention) for debugging; production input files are not retained by default.
- **Cleanup:** Background task prunes files older than X days.

### Export to GitHub

Future capability:

- Admin/superuser action: "Export Active Version"
- Downloads zip with `tools/<slug>/v<version>.py` + `metadata.json`
- DB remains authoring system; GitHub becomes curated canonical history

---

## Success Criteria

- Time from approval to runnable tool: < 30 minutes (admin workflow)
- Rollback execution: < 2 minutes
- Script execution failures surface actionable logs for admins
- No script crash affects API server stability

---

## Migration Path

### v0.2 (this epic)

- tool_versions table + active_version_id
- Draft save + sandbox run + publish active
- Docker runner with timeouts/limits
- Store run record and logs
- Admin UI: editor + run + publish

### Future Enhancements

- Diff view between versions
- Fixture library (saved test inputs)
- Per-tool capabilities (network on/off)
- Export-to-GitHub UI
- Async job queue for long-running scripts
