---
type: reference
id: REF-SKRIPT-GENERAL-ai-completion-architecture-technical-specification-PART-01
title: AI Completion Architecture Technical Specification — part 01
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-ai-completion-architecture-technical-specification
part: 1
---

## Overview

Technical architecture for AI-assisted editor features in Skriptoteket: inline completions and chat-first editing.

______________________________________________________________________

The AI editor system provides Copilot-style ghost text suggestions and a chat-first assistant for proposing safe edits.
It integrates with the CodeMirror 6 intelligence bundle. Every model call goes through HuleEdu's LLM provider door
(the OpenAI Responses route) with the signed-in teacher's user id. Skriptoteket holds no provider key and no local
model endpoint.

**Capabilities:**

| Capability                      | Story    | Model                          | Description                                                                |
| ------------------------------- | -------- | ------------------------------ | -------------------------------------------------------------------------- |
| Inline completions (ghost text) | ST-08-14 | `gpt-6-luna`, reasoning `none` | Insert-only suggestion at the cursor from a delimited prefix/suffix prompt |
| Chat (SSE)                      | ADR-0051 | `gpt-6.1-sol`, reasoning `low` | Streamed answer on a server-side thread                                    |
| Chat ops (edit)                 | ADR-0051 | `gpt-6.1-sol`, reasoning `low` | Structured patch-only ops + diff preview + apply/undo                      |

**Key features:**

- Ghost text appears after typing pause (debounced auto-trigger)
- Manual trigger via Alt+\\ keyboard shortcut
- Tab to accept, Escape to dismiss
- Knowledge base injection for Skriptoteket-specific patterns
- Chat-first editing uses structured operations with diff preview + atomic apply/undo (ADR-0051)
- Chat-first editing uses “virtual files” (e.g. `tool.py`, `input_schema.json`, `settings_schema.json`) to prevent
  boundary violations while still allowing multi-document proposals
- A door daily limit surfaces as HTTP 429 `AI_DAILY_LIMIT_REACHED` with the teacher note inline in the editor's AI area

______________________________________________________________________

## Facts And Semantics

### Source: 1.1 Chat-first editing (virtual files + multi-turn)

Chat-first editing is defined in ADR-0051 and implemented via stories ST-08-20/21/22.

Key implications for architecture:

- Multi-turn context is server-side: chat-first endpoints use a canonical chat
  thread keyed by `{user_id, tool_id}` (30-day TTL since last activity) and
  the frontend sends only the newest user message.
- Proposals must target an explicit virtual file to keep diffs and apply/undo reliable.
- Output token budgets for proposals exceed inline completion defaults (8,192 versus 64 tokens) and are coordinated with
  the backend budgeting (ADR-0052, section 5.3).

### Source: 2. Prompt Shape

**Inline completion** sends one Responses call. The system prompt (`instructions`) is composed from the template
`inline_completion_gpt5_v1` (section 5). The single user message is a delimited prompt built by
`infrastructure/llm/openai/inline_completion_prompt.py`:

```text
<FILE>tool.py</FILE>
<LANGUAGE>python</LANGUAGE>

<PREFIX>
...code before the cursor...
</PREFIX>

<SUFFIX>
...code after the cursor...
</SUFFIX>

<CURSOR>
Return only the insertion text.
```

`<FILE>` and `<LANGUAGE>` appear only when the request names an active file; the language is derived from the extension
(`.py`, `.json`, `.md`, `.txt`). The model returns the insertion text only. Fill-in-the-middle tokens and grammar-
constrained decoding are not used.

**Chat** sends the thread messages as `input` items with the composed system prompt as `instructions` and `stream: true`.

**Chat ops** sends the same message shape with `stream: false` and a `text.format` of type `json_schema`
(`edit_ops_patch_only`, built in `infrastructure/llm/openai/edit_ops_text_format.py`). The schema holds
`assistant_message` and `ops`; each op is a `patch` with a `target_file` (one virtual file) and `patch_lines`.

### Source: 3. Infrastructure Architecture

### 3.1 Door Routing

```text
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────────┐     ┌────────────┐
│  CodeMirror 6   │────▶│  Backend        │────▶│  HuleEdu LLM         │────▶│  OpenAI    │
│  (Frontend)     │     │  (FastAPI)      │     │  provider door       │     │  Responses │
└─────────────────┘     └─────────────────┘     └──────────────────────┘     └────────────┘
                         KB injection            meters pools, shares,
                         + auth + CSRF           USD ceiling
```

- One module, `infrastructure/llm/door/client.py` (`HuleEduLlmDoorClient`), reaches the door. The three providers in
  `infrastructure/llm/openai/` (inline completion, chat stream, chat ops) build a Responses body and call it through
  `LlmDoorClientProtocol`.
- Route: `POST {HULEEDU_LLM_PROVIDER_BASE_URL}/internal/v1/openai/responses`, authenticated with
  `X-Internal-API-Key` (`HULEEDU_INTERNAL_API_KEY`) and `X-Service-ID: skriptoteket`. The door resolves provider
  credentials; Skriptoteket never sees them.
- The call carries `X-HuleEdu-User-ID` (the teacher), `X-HuleEdu-OpenAI-Allowance-Mode`, and
  `X-HuleEdu-Exempt-Test-User: true` for admins.
- Each editor request starts its own `AiDoorCaller` (`door_caller_for(user=actor)`); the handlers pass it to the provider.
- Pools: inline completion draws on the small-model pool (`gpt-6-luna`); chat, chat ops and edit draw on the
  full-model pool (`gpt-6.1-sol`). The door prices a model only when its manifest has the entry.
- Neither model accepts `temperature`. The body carries no temperature, no stop sequences, no prompt-cache key or
  retention and no extra headers; the door owns caching.
- There is no failover route and no provider choice: one model per capability, one path.

### 3.2 Request Body

`infrastructure/llm/openai/payloads.py` (`build_responses_payload`) builds every editor body:

| Field                 | Source                                                               |
| --------------------- | -------------------------------------------------------------------- |
| `model`               | `LLM_*_MODEL`                                                        |
| `instructions`        | Composed system prompt                                               |
| `input`               | `message` items (`input_text` for user, `output_text` for assistant) |
| `max_output_tokens`   | `LLM_*_MAX_TOKENS`                                                   |
| `reasoning.effort`    | `LLM_*_REASONING_EFFORT`                                             |
| `text.verbosity`      | `LLM_*_TEXT_VERBOSITY` (omitted when `None`)                         |
| `text.format`         | Chat ops only: the patch-only JSON schema                            |
| `stream`              | `true` for chat, `false` otherwise                                   |
| `store`, `truncation` | Inline completion only: `false`, `auto`                              |

### 3.3 Failures

`infrastructure/llm/openai/door_replies.py` maps a door answer to `EditorLlmProviderError`
(`protocols/llm/common.py`):

| Kind                      | Cause                                                                                    |
| ------------------------- | ---------------------------------------------------------------------------------------- |
| `timeout`                 | Door call exceeded `LLM_*_TIMEOUT_SECONDS`                                               |
| `request_failed`          | Transport failed before an answer                                                        |
| `context_window_exceeded` | Relayed OpenAI error code `context_length_exceeded`                                      |
| `http_status`             | Any other unsuccessful relayed answer (a door capacity 429 included), with `status_code` |
| `invalid_response`        | Answer or stream event that cannot be parsed, or a stream `error` event                  |

A door daily limit is never `EditorLlmProviderError`. The door client raises `AiDailyLimitReached(limit)`
(`pool`, `user_share` or `usd_ceiling`), which the handlers turn into the 429 described in section 6.3. It is never
retried.

______________________________________________________________________

### Source: 4. Models

| Capability        | Setting                | Default       | Reasoning |
| ----------------- | ---------------------- | ------------- | --------- |
| Inline completion | `LLM_COMPLETION_MODEL` | `gpt-6-luna`  | `none`    |
| Chat              | `LLM_CHAT_MODEL`       | `gpt-6.1-sol` | `low`     |
| Chat ops (edit)   | `LLM_CHAT_OPS_MODEL`   | `gpt-6.1-sol` | `low`     |

The model ids are settings; changing one changes the pool the door meters. Token counting for budgets uses the model's
`tiktoken` encoding with an `o200k_base` fallback (`infrastructure/llm/token_counter_resolver.py`).

______________________________________________________________________

### Source: 5. Knowledge Base Injection

The backend injects Skriptoteket's knowledge base into the **system prompt** (`instructions`). The user content carries
the delimited prefix/suffix (completion) or the thread messages (chat, chat ops). The KB is high-priority instruction
content.

This ensures the LLM understands:

- Runner constraints (no network, sandbox environment)
- Contract v2 format (outputs, next_actions, state)
- Available helpers (pdf_helper, tool_errors)
- Input/output conventions (SKRIPTOTEKET_INPUT_MANIFEST)

### 5.1 Condensed KB (~450 tokens)

For injection into prompts (example content). In production we compose the system prompt from a repo-owned prompt
template selected by `LLM_COMPLETION_TEMPLATE_ID` / `LLM_CHAT_TEMPLATE_ID` / `LLM_CHAT_OPS_TEMPLATE_ID`, with
code-owned fragments (Contract v2 + runner constraints + helpers) (ST-08-18).

```text
Skriptoteket Python script completion. Scripts process uploaded files and return structured results.

ENTRYPOINT:
def run_tool(input_dir: str, output_dir: str) -> dict:

FILE INPUT (always use manifest):
import json, os
from pathlib import Path
manifest = json.loads(os.environ.get("SKRIPTOTEKET_INPUT_MANIFEST", "{}"))
files = [Path(f["path"]) for f in manifest.get("files", [])]
path = files[0] if files else None

RETURN FORMAT (Contract v2):
return {
    "outputs": [...],      # UI elements
    "next_actions": [],    # empty for now
    "state": None          # optional dict
}

OUTPUT KINDS:
{"kind": "notice", "level": "info"|"warning"|"error", "message": "..."}
{"kind": "markdown", "markdown": "## Title\n\nText with **bold**."}
{"kind": "table", "title": "...", "columns": [{"key": "k", "label": "L"}], "rows": [{"k": "v"}]}
{"kind": "json", "title": "...", "value": {...}}
{"kind": "html_sandboxed", "html": "<p>...</p>"}

ERROR PATTERN:
if path is None:
    return {"outputs": [{"kind": "notice", "level": "error", "message": "Ingen fil uppladdad"}], "next_actions": [], "state": None}

ARTIFACTS (downloadable files):
output = Path(output_dir)
output.mkdir(parents=True, exist_ok=True)
(output / "result.txt").write_text(content, encoding="utf-8")

HELPERS:
from pdf_helper import save_as_pdf  # save_as_pdf(html, output_dir, filename) -> path
from tool_errors import ToolUserError  # raise ToolUserError("User message")

CONSTRAINTS:
- No network (--network none)
- Timeout: 120s
- Memory: 1GB
- Swedish UI messages preferred

LIBRARIES: pandas, openpyxl, pypdf, python-docx, weasyprint, jinja2
```

### 5.2 Production Requirements

- **Loading strategy:** Load template text from disk (cached) and compose the system prompt per request
- **Packaging strategy:** Ship prompt templates with the application (`src/skriptoteket/application/editor/system_prompts/`)
- **Failure mode:** If a prompt template cannot be loaded or composed, return `{ "completion": "", "enabled": false }`

### 5.3 Context Budget Enforcement

The backend keeps each prompt inside a configured token budget before it calls the door. The context window settings
(`LLM_*_CONTEXT_WINDOW_TOKENS`) are Skriptoteket's own budgeting numbers; no inference server enforces them.
The prompt budget is `context window - max output tokens - safety margin`, so raising `max_tokens` lowers the prompt
budget unless the window is raised with it.

Chat-first editing proposals (ADR-0051) need larger outputs than inline completions, so chat and chat ops use a
64k-token window and 8,192 output tokens, against 4,096 and 64 for completions.

Skriptoteket enforces a deterministic prompt budget in the backend:

- Use the dedicated system prompt templates (selected by template ID):
  - `LLM_COMPLETION_TEMPLATE_ID` (inline completions)
  - `LLM_CHAT_TEMPLATE_ID` (chat streaming)
  - `LLM_CHAT_OPS_TEMPLATE_ID` (chat edit-ops)
- Reserve an explicit safety margin
- Inline completion: when the target sizes (system prompt, prefix, suffix) exceed the budget, trim the prefix first
  (keeping the tail next to the cursor), then the suffix (keeping its head), then the system prompt
- Chat: drop the oldest turns first and never truncate the system prompt (section 6.4)

Token counts come from the model's `tiktoken` encoding through `TokenCounterResolverProtocol`. Budgeting lives in
`src/skriptoteket/application/editor/prompt_budget.py`; budgets for chat and chat ops resolve from settings in
`infrastructure/llm/chat_budget_resolver.py` and `chat_ops_budget_resolver.py`.

______________________________________________________________________

### Source: 6. API Contract

### 6.1 Request

```
POST /api/v1/editor/completions
Content-Type: application/json
X-CSRFToken: <csrf_token>

{
  "prefix": "<code before cursor>",
  "suffix": "<code after cursor>",
  "active_file": "tool.py"
}
```

Notes:

- `active_file` is a virtual file id and defaults to `tool.py`.
- The API accepts large `prefix`/`suffix` strings, but the backend trims them deterministically to fit the configured
  context budget (see 5.3).
- Access requires `require_app_ai_api` (admin or superuser), a temporary gate until the AI spend limits ship
  (TASK-SKRIPT-REP-0044). Chat (`POST`) and edit-ops (`POST /edit-ops`) use the same gate.

### 6.2 Response

```json
{
  "completion": "<suggested code to insert>",
  "enabled": true,
  "replace_suffix_chars": 3
}
```

Notes:

- `completion` MAY contain newline characters (`\n`) and should be inserted verbatim
- `replace_suffix_chars` is present only when normalization asks the client to replace that many characters after the
  cursor
- The backend MUST NOT surface truncated completions. If the finish reason is `length` or `incomplete`, return empty
  completion
- Normalization (`application/editor/completion/normalization.py`) strips code fences, trims overlap with the prefix
  and suffix (512-character window), drops echoes of the surrounding code, and may set `replace_suffix_chars`
  (at most 24)

### 6.3 Error Handling

| Scenario                                  | Response                                                                                                                     |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| LLM disabled                              | `{ "completion": "", "enabled": false }`                                                                                     |
| KB unavailable                            | `{ "completion": "", "enabled": false }`                                                                                     |
| Door timeout                              | `{ "completion": "", "enabled": true }`                                                                                      |
| Door error (any `EditorLlmProviderError`) | `{ "completion": "", "enabled": true }`                                                                                      |
| Upstream truncated                        | `{ "completion": "", "enabled": true }`                                                                                      |
| Door daily limit                          | HTTP 429, code `AI_DAILY_LIMIT_REACHED`, `details.limit` (`pool`, `user_share` or `usd_ceiling`), message = the teacher note |
| Unauthorized                              | HTTP 401                                                                                                                     |
| Missing CSRF                              | HTTP 403                                                                                                                     |

The teacher note (`ai_limit_note`) is `Du har nått din gräns för AI-hjälp i dag. Försök igen i morgon.` for the user's
own share and `Appens AI-hjälp har nått dagens gräns. Försök igen i morgon.` for the app's pool or USD ceiling. The
SPA shows it inline in the editor's AI area (ghost text, chat and edit-ops share one limit state) and shows no toast.

Chat ops (`POST /api/v1/editor/edit-ops`) returns the same 429 and records the turn as failed with the note as the
assistant message.

### 6.4 Editor chat streaming (SSE)

```
POST /api/v1/editor/tools/{tool_id}/chat
Content-Type: application/json
X-CSRF-Token: <csrf_token>

{
  "message": "..."
}
```

Response is **SSE** (`Content-Type: text/event-stream; charset=utf-8`, `Cache-Control: no-cache`) with stable event
types:

- `event: meta` (exactly once, first): `data: {"enabled": true}`
- `event: delta` (0..n): `data: {"text": "<utf8-chunk>"}`
- `event: done` (exactly once, last): `data: {"enabled": true, "reason": "stop"|"cancelled"|"error"}`
- If disabled/misconfigured: a single `event: done` with `data: {"enabled": false, "message": "<svenska>"}`
- A door daily limit is refused before the first SSE event: the request fails with the HTTP 429 above, so the stream
  never opens.
- Any other door failure ends the stream with `done` and `reason: "error"` (after `meta`).

Canonical thread behavior:

- Conversation history is stored server-side per `{user_id, tool_id}` and used
  as context on subsequent chat-first requests (30-day TTL since last
  activity).
- Clear the thread via `DELETE /api/v1/editor/tools/{tool_id}/chat`; read it via `GET` on the same path.
- Provider calls use a sliding window (drop oldest turns first) and never
  truncate the system prompt.
- If the newest user message cannot fit with the full system prompt and
  reserved output budget: return HTTP 422 with
  `För långt meddelande: korta ned eller starta en ny chatt.` (and do not
  mutate stored history).

Client rule:

- If the SSE connection closes before a `done` event is received, treat the stream as cancelled.

### 6.5 Edit-ops preview and apply

- `POST /api/v1/editor/edit-ops` runs the chat-ops model call and returns `assistant_message`, `ops` and
  `base_fingerprints`.
- `POST /api/v1/editor/edit-ops/preview` validates ops against the virtual files and returns `after_virtual_files`,
  `errors` and `meta`. It makes no model call.
- `POST /api/v1/editor/edit-ops/apply` applies ops atomically with `base_hash` and `patch_id` checks. It makes no
  model call. Both require contributor access to the tool.

______________________________________________________________________

### Source: 7. CodeMirror Extension Architecture
