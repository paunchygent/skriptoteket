---
type: prd
id: PRD-script-hub-v0.2
title: "Script Hub PRD v0.2 Features (Planned)"
status: draft
owners: "agents"
created: 2025-12-17
product: "script-hub"
version: "0.2"
---

## Summary

This document outlines key features planned for the post-MVP (v0.2) release of the Script Hub. The primary focus is enabling **stateful, multi-turn tools** with a **safe, typed UI contract** (outputs + actions + persisted state) and paving the way for curated “owner apps” without exposing arbitrary UI/JS to end users.

## Related v0.1 enabling work

- Tool authoring (admin quick-create + slug lifecycle): `docs/prd/prd-tool-authoring-v0.1.md`
- ADR: tool slug lifecycle: `docs/adr/adr-0037-tool-slug-lifecycle.md`
- Epic: admin tool authoring: `docs/backlog/epics/epic-14-admin-tool-authoring.md`

## Feature: Tool Sessions (User-Specific State)

### Context & Problem
Currently, tools are **stateless**. Every execution is an isolated event. This prevents tools from:
1.  Remembering past actions (e.g., "Skip rows I processed yesterday").
2.  Learning user preferences (e.g., "Default to 'Class 9B' for this user").
3.  Providing incremental processing (e.g., "Compare this upload to the last one").

### Solution
Implement a **small, persistent, user-specific JSON state** for each tool, stored as a “tool session”.

### Technical Requirements
1.  **Storage**: New table `tool_sessions` keyed by (`tool_id`, `user_id`, `context`) with:
    - `state` JSONB (size-capped)
    - `state_rev` integer (optimistic concurrency)
2.  **Injection**: The platform injects the prior session state into each execution request (as structured JSON), not via ad-hoc artifacts.
3.  **Extraction**: The execution result returns updated `state` which the platform validates, size-caps, and persists.
4.  **Concurrency**: Use `expected_state_rev` on each “turn”; reject stale updates (multi-tab safety).
5.  **Controls**: Users must have a “Clear memory” action to reset session state.

### User Story
> "As a Special Educator, I want the 'Attendance Analyzer' to remember which students I flagged last week, so I don't have to manually filter them out of this week's report."

## Feature: Interactive Tool UI (Outputs + Actions + State)

### Context & Problem
Currently, script execution is **linear**: Input -> Processing -> Final Output.
Complex tasks often require a **human-in-the-loop** to verify or organize data (e.g., grouping students into breakout sessions) before finalizing the result. Doing this strictly via file re-uploads is tedious.

### Solution
Adopt a **typed tool UI contract** where each “turn” returns:

- `outputs[]`: structured, platform-rendered UI blocks (tables, markdown, JSON viewers, artifact previews)
- `next_actions[]`: a list of allowed next steps with an input schema (the platform renders forms)
- `state`: small persisted JSON, used to preserve multi-turn state across sessions

Interactivity is provided by the platform’s UI components (safe), not arbitrary script-provided JavaScript.

### Technical Requirements
1.  **Dependencies**: Requires **Tool Sessions** (above).
2.  **Contract**: Extend the runner result contract to return structured `outputs`, `next_actions`, and `state` (contract v2).
3.  **Frontend**:
    - Renders outputs using allowlisted UI components (no custom JS from tools).
    - Renders action forms based on a constrained schema (platform-defined).
4.  **Feedback loop**:
    - Users invoke actions (turn-taking).
    - Each action produces a new run + updated state.
    - The platform persists state and rehydrates it for the next turn.

### Implementation Notes

- UI paradigm: full Vue/Vite SPA (ADR-0027).

### User Story
> "As a Teacher creating seating charts, I want to upload my class list and see a drag-and-drop grid. The system should remember where I placed specific students last time so I only have to assign the new transfer student."

## Feature: Advanced Input Handling (Multi-File & External Sources)

### Context & Problem
The v0.1 runner restricts inputs to a **single file**.
Real-world tasks often require correlating data from multiple sources (e.g., "Compare *this month's* schedule with *last month's* absence list") or fetching data from external systems (e.g., LMS, HR system) rather than requiring the user to manually download and re-upload files.

### Solution
Expand the execution model to support **Multiple Inputs**.
"Inputs" can be direct file uploads or references to external data sources that the platform fetches and bundles before execution.

### Technical Requirements
1.  **Frontend**:
    *   Upgrade the upload form to support multiple files (e.g., specific slots like "Source A", "Source B" or a generic "Add File" list).
    *   (Future) Add "Import from..." buttons that fetch data on the client-side or trigger backend fetchers.
2.  **Protocol (Command)**:
    *   Update `RunActiveToolCommand` to accept `inputs: List[InputArtifact]` instead of single `input_bytes`.
3.  **Runner**:
    *   **Container Layout**: Map all inputs into the `/work/input/` directory.
    *   **Env Var**: Provide `SKRIPTOTEKET_INPUT_MANIFEST` (JSON) listing available files and their metadata (source, original name).
4.  **Script Contract**:
    *   Scripts must be able to handle iterating through `/work/input/` or looking for specific filenames.
    *   Provide `SKRIPTOTEKET_INPUT_DIR=/work/input` and `SKRIPTOTEKET_INPUT_MANIFEST` for deterministic discovery.

### User Story
> "As an Administrator, I want to upload the 'Budget Report' and the 'Staff List' simultaneously so the script can calculate the cost per department without me having to merge the Excel files manually first."

## Feature: Native PDF Output Support

### Context & Problem
Scripts generate HTML for immediate viewing. However, many administrative workflows (signing, archiving, emailing) require **PDF documents**.
Currently, users must use their browser's "Print to PDF" function, which often breaks formatting and lacks professional polish (headers, footers, page breaks).

### Solution
Equip the runner environment with a high-fidelity HTML-to-PDF engine (e.g., WeasyPrint) and provide a simple API for scripts to generate PDF artifacts.

### Technical Requirements
1.  **Runner Environment**:
    *   Pre-install `WeasyPrint` (Python library) in the `skriptoteket-runner` image.
    *   (Note: System dependencies like `libpango` and `libcairo` are already present in the Dockerfile).
2.  **Script Helper**:
    *   Inject a helper module or function (e.g., `save_as_pdf(html_string, filename)`) so script authors don't need complex boilerplate.
3.  **Output**:
    *   Scripts save the generated PDF to `/work/output/`.
    *   The platform automatically picks it up as a downloadable artifact.

### User Story
> "As a Principal, I want the 'Incident Report' tool to produce a properly formatted PDF with the school logo and page numbers, so I can file it immediately without formatting it myself."

## Feature: Personalize Tool Output (Persisted Styles)

### Context & Problem
Different users have different needs for how information is presented.
*   **Accessibility:** Some users need larger fonts or high-contrast themes.
*   **Branding:** Different schools need their specific logos or header colors on reports.
*   **Preference:** Some users prefer "Dense Tables" while others want "Summary Cards".
Currently, scripts are "one size fits all" unless the user manually uploads a settings file every time.

### Solution
Standardize a **"Tool Settings"** interface.
Scripts can declare configurable style options (color, layout, font size). The platform generates a settings form, and the user's choices are automatically **saved to their Tool Memory** and injected into every future run.

### Technical Requirements
1.  **Schema**: Scripts can optionally provide a `settings_schema.json` (defining fields like `theme_color`, `font_size`, `logo_url`).
2.  **UI**: The platform renders a "Settings" (⚙️) panel next to the "Run" button based on the schema.
3.  **Persistence**: Values are stored in the existing `tool_user_state` (User Memory).
4.  **Injection**: Settings are merged into the `memory.json` injected into the runner, so the script can simply read `memory['settings']['theme_color']` to style its HTML/PDF output.

### User Story
> "As a User with low vision, I want to set the 'Font Size' to 'Large' for the 'Weekly Letter' tool and have it remember that preference every time I generate a PDF."

## Feature: Tool-Managed Datasets (Saved Rosters & Reusable Lists)

### Context & Problem
Tool settings are a single key-value dict. That works for defaults, but not for reusable lists such as class rosters,
group sets, or templates. Users need CRUD-style data that can be selected per run.

### Solution
Add a per-user **dataset library** scoped to a tool. A tool can:

- Read a named dataset (e.g., "Class 9B roster")
- Offer a "Save as dataset" suggestion after a run
- Allow the user to choose which dataset to use for the next run

### Technical Requirements
1. **Storage**: New table (e.g., `tool_datasets`) keyed by (`tool_id`, `user_id`, `name`) with JSON payload + size caps.
2. **API**: CRUD endpoints for dataset list/read/write/delete; optimistic concurrency for edits.
3. **UI**: Dataset picker in tool run view + save prompts (ties to "settings suggestions" UX).
4. **Runner injection**: Include selected dataset(s) under `memory` for deterministic reads.

### User Story
> "As a Teacher, I want to save my class roster once and reuse it in multiple tools without re-uploading the same list."

## Feature: User File Vault (Reusable Uploads & Artifacts)

### Context & Problem
Users often re-upload the same files (rosters, templates, reports). Artifacts are produced, but not reusable as inputs.

### Solution
Introduce a **user file vault** so users can select prior uploads or outputs as inputs for new runs.
This pairs naturally with first-class file references (ST-14-24).

### Technical Requirements
1. **Storage**: Metadata table for user-owned files + lifecycle policies.
2. **UI**: File picker in tool run view ("Choose from vault") and in action forms when file references are allowed.
3. **Runner**: Stage selected files into `/work/input/` using safe paths; no direct filesystem paths in UI.
4. **Security**: Access scoped to user (and shared links, if enabled).

### User Story
> "As a Counselor, I want to reuse last month's roster file without uploading it again."

## Feature: Integrated NLP Services (Grammar & Text Analysis)

### Context & Problem
Teachers frequently need to analyze student texts for readability (LIX/word counts) or grammar correctness.
Implementing this in individual scripts is inefficient because:
1.  **Size:** NLP models (spaCy) and tools (LanguageTool) are massive (GBs), making the runner image bloated.
2.  **Complexity:** Script authors shouldn't need to be NLP experts to get basic metrics.
3.  **Performance:** Loading models for every 5-second script run is too slow.

### Solution
Integrate NLP capabilities as **backend-executed actions** that produce typed outputs (tables, metrics, annotations).
This keeps the runner network-isolated and centralizes access control, quotas, and observability.

### Technical Requirements
1.  **Backend capability surface**:
    - Backend connects to the NLP service (internal) and exposes allowlisted “capability actions” (e.g. `cap.nlp.analyze_language`).
2.  **Authorization & quotas**:
    - Only enabled for specific tools or curated apps (policy-driven).
3.  **Outputs**:
    - Results are returned as typed outputs (e.g. metrics table, findings list), not as HTML/JS.

### User Story
> "As a Language Teacher, I want to upload a folder of student essays and get a summary table showing the LIX score and common grammar mistakes for each student, without me having to check them manually."

## Feature: Automation & Secure Connectors (Scheduled Runs + External Data)

### Context & Problem
Some tools should run on a schedule or pull data from external systems (Sheets, LMS, HR). The runner is intentionally
network-isolated, so direct access from scripts is not viable.

### Solution
Add a **platform-managed automation layer**:

- Scheduled/batch runs that execute tools at defined times
- Allowlisted connectors (Sheets/Drive/SSO APIs) mediated by backend services
- Secrets stored and injected only into the connector layer, never into runner containers

### Technical Requirements
1. **Scheduler**: A job service with queues and run history.
2. **Connectors**: Proxy layer with allowlists + auditing; no general outbound network from runner.
3. **Secrets**: Store per-tenant/connector credentials with audit trails and rotation.
4. **Runs**: Scheduled runs still produce normal tool runs + artifacts for the user.

### User Story
> "As a Principal, I want a weekly absence report generated automatically from a Google Sheet without manual uploads."

## Feature: Author Analytics & Health Metrics

### Context & Problem
Tool authors and admins lack visibility into usage and failure patterns, making it hard to iterate safely.

### Solution
Expose a lightweight analytics panel for maintainers and admins:

- Run volume trends (per tool/version)
- Success/failure rate with top error summaries
- Common inputs/settings (aggregated, privacy-safe)

### Technical Requirements
1. **Aggregation**: Query/rollup over `tool_runs` (and errors) with indexes.
2. **UI**: Admin/maintainer dashboard views (no PII exposure).
3. **Policy**: Only maintainers/admins can view analytics; no end-user tracking.

### User Story
> "As a Maintainer, I want to see if a new version caused a spike in failures so I can roll back quickly."

## Feature: Collaboration Primitives (Share Runs, Templates, Settings)

### Context & Problem
Teachers often need to share a run result or a starting template with colleagues. Today, settings and runs are
per-user and not shareable.

### Solution
Provide opt-in sharing of:

- A run result (read-only link)
- A settings template (copy into my settings)
- A dataset snapshot (copy into my datasets)

### Technical Requirements
1. **Sharing model**: Share tokens or ACL-based access with expiration.
2. **UI**: "Share" action in run details + "Copy to my settings/datasets" flows.
3. **Security**: Explicit owner consent; audit trail of shares.

### User Story
> "As a Special Educator, I want to share a grouped seating plan with a colleague who supports the same class."

## Feature: Interactive Inputs (Placeholder)
*To be defined: Support for text/dropdown inputs in addition to file uploads.*

## Feature: Curated Apps (Owner-Authored, Platform-Rendered UI)

### Context & Problem
Some “apps” should be more capable than user-authored scripts (advanced flows, richer outputs, deeper backend integrations),
but exposing those capabilities broadly increases security and UX risk.

### Solution
Introduce a curated app registry shipped with the repo (or a trusted package) that:

- is visible in Katalog (like tools)
- is runnable by end users
- is **not** editable via the tool editor UI
- is **not** versioned via `tool_versions`
- returns typed outputs/actions/state and is rendered by the platform UI (same contract, higher policy caps)

### Technical Requirements
1. Registry: a curated app list with `app_id`, `app_version`, metadata, and a minimum required role.
2. Execution: a curated app execution path that can call internal services safely and emits the same typed UI contract.
3. Persistence: runs are stored for auditability with a `source_kind` distinguishing curated runs from tool-version runs.
