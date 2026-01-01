---
type: reference
id: REF-ai-completion-architecture
title: "AI Completion Architecture Technical Specification"
status: active
owners: "agents"
created: 2025-12-26
updated: 2025-12-30
topic: "ai-completion"
---

Technical architecture for AI-assisted code completions in the Skriptoteket script editor.

---

## 1. Overview

The AI completion system provides Copilot-style ghost text suggestions while users write scripts. It integrates with the
CodeMirror 6 intelligence bundle and supports both self-hosted and API-based LLM providers.

**Capabilities:**

| Capability | Story | Description |
| ---------- | ----- | ----------- |
| Inline completions (ghost text) | ST-08-14 | FIM-based code suggestions at cursor |
| Chat/edit suggestions | ST-08-16 | Chat-based code modifications (separate protocol) |

**Key features:**

- Ghost text appears after typing pause (debounced auto-trigger)
- Manual trigger via Alt+\ keyboard shortcut
- Tab to accept, Escape to dismiss
- Knowledge base injection for Skriptoteket-specific patterns
- Works with self-hosted (Tabby/llama.cpp) and API providers

---

## 2. FIM Token Interpolation

**FIM (Fill-in-the-Middle)** is a prompting technique for code completion where the model receives:

- **Prefix**: Code before the cursor position
- **Suffix**: Code after the cursor position
- **Middle token**: Signals where to generate the completion

Example with Qwen FIM tokens:

```text
<|fim_prefix|>def hello(name):
    greeting = f"Hello, {name}!"
    <|fim_suffix|>
    return greeting<|fim_middle|>
```

The model generates what belongs between prefix and suffix (e.g., `# Format the greeting`).

### 2.1 Model-Specific FIM Tokens

| Model Family | Prefix | Suffix | Middle |
| ------------ | ------ | ------ | ------ |
| Qwen3-Coder | `<\|fim_prefix\|>` | `<\|fim_suffix\|>` | `<\|fim_middle\|>` |
| CodeLlama | `<PRE>` | `<SUF>` | `<MID>` |
| StarCoder | `<fim_prefix>` | `<fim_suffix>` | `<fim_middle>` |

---

## 3. Infrastructure Architecture

### 3.1 Self-Hosted Stack (Current)

```text
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  CodeMirror 6   │────▶│  Backend Proxy  │────▶│  llama.cpp      │
│  (Frontend)     │     │  (FastAPI)      │     │  :8082 (ROCm)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                         KB injection            Qwen3-Coder-30B-A3B
                         + auth + CSRF
```

See [ADR-0050](../adr/adr-0050-self-hosted-llm-infrastructure.md) for infrastructure details.

### 3.2 Tabby Integration (Optional)

Tabby can serve as an intermediary for repository indexing and caching:

```text
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Backend Proxy  │────▶│  Tabby :8083    │────▶│  llama.cpp      │
│  (FastAPI)      │     │                 │     │  :8082          │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 3.3 Tabby Customization Options

Based on [Tabby documentation](https://tabby.tabbyml.com/docs/administration/config-toml/):

| Feature | Scope | Custom Context? | Notes |
| ------- | ----- | --------------- | ----- |
| `prompt_template` | FIM completion | ❌ | Only `{prefix}` and `{suffix}` placeholders |
| `[answer] system_prompt` | Chat/Answer Engine | ✅ | Full system prompt customization |
| `[[repositories]]` | Both | ✅ | Indexes code, injects relevant snippets |
| `max_input_length` | Completion | — | Context window (default 1536 chars) |
| `max_decoding_tokens` | Completion | — | Output length (default 64 tokens) |

**Key limitation:** Tabby's `prompt_template` only interpolates `{prefix}` and `{suffix}`. Arbitrary context prefixes
cause parsing errors. For KB injection, use the backend proxy or Tabby's chat endpoint with `[answer] system_prompt`.

### 3.4 Integration Options

| Option | Architecture | KB Injection | Pros | Cons |
| ------ | ------------ | ------------ | ---- | ---- |
| A: Backend → llama.cpp | Direct | In prompt prefix | Full control, FIM format | No Tabby features |
| B: Backend → Tabby chat | `/v1/chat/completions` | System prompt | Native Tabby, repo context | Chat format, not FIM |
| C: Backend → Tabby FIM | `/v1/completions` | None (Tabby limitation) | Fast, caching | No custom KB |

**Recommended:** Option A for inline completions (full KB control), Option B for chat/edit suggestions.

---

## 4. Recommended Models (December 2025)

### 4.1 Self-Hosted

| Model | Architecture | VRAM | Context | Use Case |
| ----- | ------------ | ---- | ------- | -------- |
| **Qwen3-Coder-30B-A3B** | MoE (3.3B active) | ~18.5 GB | 262K | FIM completions (current) |
| **Kimi K2** | Open-source | Varies | - | Alternative for code |

### 4.2 API Providers

| Provider | Model | Use Case |
| -------- | ----- | -------- |
| Anthropic | **Claude Opus 4.5** | High-quality completions |
| OpenAI | **GPT-5-2-Codex** | Code-specialized model |
| OpenAI | **GPT-5-2** | Dense big model |
| OpenAI | **GPT-5.2 High** | Planning model (chat, more reliable than Opus 4.5) |

### 4.3 Configuration Examples

**Self-hosted (Qwen3-Coder via llama.cpp):**

```bash
LLM_COMPLETION_ENABLED=true
LLM_COMPLETION_BASE_URL=http://localhost:8082
LLM_COMPLETION_MODEL=qwen3-coder-30b-a3b
LLM_COMPLETION_MAX_TOKENS=256
LLM_COMPLETION_TEMPERATURE=0.2
```

**API Provider (Claude Opus 4.5):**

```bash
LLM_COMPLETION_ENABLED=true
LLM_COMPLETION_BASE_URL=https://api.anthropic.com/v1
OPENAI_LLM_COMPLETION_API_KEY=sk-ant-...
LLM_COMPLETION_MODEL=claude-opus-4.5
```

**API Provider (GPT-5-2-Codex):**

```bash
LLM_COMPLETION_ENABLED=true
LLM_COMPLETION_BASE_URL=https://api.openai.com/v1
OPENAI_LLM_COMPLETION_API_KEY=sk-...
LLM_COMPLETION_MODEL=gpt-5-2-codex
```

---

## 5. Knowledge Base Injection

The backend injects Skriptoteket's knowledge base into the **system prompt** (chat system message). Inline completions
still use FIM prompting for the **user** content (prefix/suffix + model FIM tokens), but the KB is treated as
high-priority instruction content.

This ensures the LLM understands:

- Runner constraints (no network, sandbox environment)
- Contract v2 format (outputs, next_actions, state)
- Available helpers (pdf_helper, tool_errors)
- Input/output conventions (SKRIPTOTEKET_INPUT_MANIFEST)

### 5.1 Condensed KB (~450 tokens)

For injection into prompts (example content). In production we compose the system prompt from a repo-owned prompt
template selected by `LLM_COMPLETION_TEMPLATE_ID` / `LLM_EDIT_TEMPLATE_ID`, with code-owned fragments (Contract v2 +
runner constraints + helpers) (ST-08-18).

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

### 5.3 Context Budget Enforcement (llama.cpp `n_ctx=4096`)

For both inline completions and edit suggestions, llama.cpp enforces that **prompt tokens + output tokens** fit within
the configured context window (`n_ctx`). This means `max_tokens` reduces the available prompt budget.

Skriptoteket enforces a deterministic prompt budget in the backend:

- Use the dedicated system prompt templates (selected by template ID):
  - `LLM_COMPLETION_TEMPLATE_ID` (inline completions)
  - `LLM_EDIT_TEMPLATE_ID` (edit suggestions)
- Reserve an explicit safety margin
- Trim suffix first, then prefix; reduce KB last (if still over budget)

Budgeting is implemented as a conservative, char-based approximation in `src/skriptoteket/application/editor/prompt_budget.py`.

---

## 6. API Contract

### 6.1 Request

```
POST /api/v1/editor/completions
Content-Type: application/json
X-CSRFToken: <csrf_token>

{
  "prefix": "<code before cursor>",
  "suffix": "<code after cursor>"
}
```

Notes:

- The API accepts large `prefix`/`suffix` strings, but the backend will trim them deterministically to fit the configured
  context budget (see 5.3).

### 6.2 Response

```json
{
  "completion": "<suggested code to insert>",
  "enabled": true
}
```

Notes:

- `completion` MAY contain newline characters (`\n`) and should be inserted verbatim
- The backend MUST NOT surface truncated completions. If `finish_reason == "length"`, return empty completion

### 6.3 Error Handling

| Scenario | Response |
| -------- | -------- |
| LLM disabled | `{ "completion": "", "enabled": false }` |
| KB unavailable | `{ "completion": "", "enabled": false }` |
| LLM timeout | `{ "completion": "", "enabled": true }` |
| LLM error | `{ "completion": "", "enabled": true }` |
| Upstream truncated | `{ "completion": "", "enabled": true }` |
| Unauthorized | HTTP 401 |
| Missing CSRF | HTTP 403 |

---

## 7. CodeMirror Extension Architecture

### 7.1 Extension Composition

```typescript
skriptoteketIntelligence(config)
├─ skriptoteketCompletions (existing)
├─ skriptoteketHover (existing)
├─ skriptoteketLinter (existing)
└─ skriptoteketGhostText (NEW)
```

### 7.2 Ghost Text State

```typescript
type GhostTextState = {
  text: string | null;     // Suggested completion
  from: number;            // Cursor position when suggested
  decorations: DecorationSet;
};
```

### 7.3 Triggers

| Trigger | Behavior |
| ------- | -------- |
| Typing pause (1500ms) | Auto-fetch completion if enabled |
| Alt+\ | Manual fetch completion |
| Tab | Accept ghost text |
| Escape | Dismiss ghost text |
| Any document change | Clear ghost text |

### 7.4 Request Management

- Cancel pending requests on document change
- Ignore stale responses (cursor moved since request)
- Debounce auto-trigger to reduce API load

---

## 8. Configuration

### 8.1 Backend (Environment Variables)

Prompt templates:

- `LLM_COMPLETION_TEMPLATE_ID` (default: `inline_completion_v1`)
- `LLM_EDIT_TEMPLATE_ID` (default: `edit_suggestion_v1`)

Notes:

- Templates are repo-owned text files with placeholders like `{{CONTRACT_V2_FRAGMENT}}`.
- Placeholders are replaced with code-owned fragments sourced from canonical Contract v2 + policy definitions.

Inline completions:

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `LLM_COMPLETION_TEMPLATE_ID` | `inline_completion_v1` | Prompt template ID for system prompt composition |
| `LLM_COMPLETION_ENABLED` | `false` | Enable/disable feature |
| `LLM_COMPLETION_BASE_URL` | `http://localhost:8082` | LLM API URL |
| `OPENAI_LLM_COMPLETION_API_KEY` | `""` | API key (optional for self-hosted) |
| `LLM_COMPLETION_MODEL` | `qwen3-coder-30b-a3b` | Model name |
| `LLM_COMPLETION_MAX_TOKENS` | `256` | Max tokens in response |
| `LLM_COMPLETION_TEMPERATURE` | `0.2` | Sampling temperature |
| `LLM_COMPLETION_TIMEOUT_SECONDS` | `30` | Request timeout |
| `LLM_COMPLETION_CONTEXT_WINDOW_TOKENS` | `4096` | Context window (prompt + output), matches llama.cpp `n_ctx` |
| `LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS` | `256` | Reserved prompt budget for chat wrapping/variance |
| `LLM_COMPLETION_SYSTEM_PROMPT_MAX_TOKENS` | `1024` | Target max tokens for system prompt (rules + KB) |
| `LLM_COMPLETION_PREFIX_MAX_TOKENS` | `2048` | Target max tokens for prefix (keeps tail near cursor) |
| `LLM_COMPLETION_SUFFIX_MAX_TOKENS` | `512` | Target max tokens for suffix (keeps head after cursor) |

Edit suggestions:

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `LLM_EDIT_TEMPLATE_ID` | `edit_suggestion_v1` | Prompt template ID for system prompt composition |
| `LLM_EDIT_ENABLED` | `false` | Enable/disable feature |
| `LLM_EDIT_BASE_URL` | `http://localhost:8082` | LLM API URL |
| `OPENAI_LLM_EDIT_API_KEY` | `""` | API key (optional for self-hosted) |
| `LLM_EDIT_MODEL` | `qwen3-coder-30b-a3b` | Model name |
| `LLM_EDIT_MAX_TOKENS` | `512` | Max tokens in response |
| `LLM_EDIT_TEMPERATURE` | `0.2` | Sampling temperature |
| `LLM_EDIT_TIMEOUT_SECONDS` | `60` | Request timeout |
| `LLM_EDIT_CONTEXT_WINDOW_TOKENS` | `4096` | Context window (prompt + output), matches llama.cpp `n_ctx` |
| `LLM_EDIT_CONTEXT_SAFETY_MARGIN_TOKENS` | `256` | Reserved prompt budget for chat wrapping/variance |
| `LLM_EDIT_SYSTEM_PROMPT_MAX_TOKENS` | `1024` | Target max tokens for system prompt (rules + KB) |
| `LLM_EDIT_INSTRUCTION_MAX_TOKENS` | `128` | Target max tokens for edit instruction |
| `LLM_EDIT_SELECTION_MAX_TOKENS` | `896` | Target max tokens for selection (preserved first) |
| `LLM_EDIT_PREFIX_MAX_TOKENS` | `1024` | Target max tokens for prefix context |
| `LLM_EDIT_SUFFIX_MAX_TOKENS` | `256` | Target max tokens for suffix context |

### 8.2 Frontend (Intelligence Config)

```typescript
type SkriptoteketIntelligenceConfig = {
  entrypointName: string;
  ghostText?: {
    enabled: boolean;       // Enable ghost text
    autoTrigger: boolean;   // Auto-trigger on typing pause
    debounceMs: number;     // Debounce delay (default: 1500)
  };
};
```

---

## 9. Security Considerations

### 9.1 API Key Protection

- API keys stored as environment variables on backend only
- Never exposed to frontend
- Backend proxies all LLM requests

### 9.2 Authentication

- Endpoint requires `require_contributor_api` (authenticated contributor+)
- CSRF token required for all POST requests

### 9.3 Rate Limiting

- Consider per-user rate limiting (10 requests/minute)
- Prevents abuse and controls costs

### 9.4 Privacy & Logging

- Do not log raw prefix/suffix/prompt/code
- Log only metadata (lengths, provider, timing, status)
- Document that remote providers receive user code; recommend self-hosted for sensitive content

---

## 10. Files

### 10.1 Backend

| Path | Purpose |
| ---- | ------- |
| `src/skriptoteket/protocols/llm.py` | Protocol definitions |
| `src/skriptoteket/infrastructure/llm/openai_provider.py` | OpenAI-compatible client |
| `src/skriptoteket/application/editor/completion_handler.py` | Handler with KB injection |
| `src/skriptoteket/di/llm.py` | DI provider |
| `src/skriptoteket/config.py` | Configuration settings |
| `src/skriptoteket/application/editor/prompt_templates.py` | Prompt template registry (IDs + required placeholders) |
| `src/skriptoteket/application/editor/prompt_fragments.py` | Code-owned fragments (Contract v2 + runner constraints + helpers) |
| `src/skriptoteket/application/editor/prompt_composer.py` | Template composition + validation (placeholders + budget) |
| `src/skriptoteket/web/api/v1/editor.py` | API endpoint |

### 10.2 Frontend

| Path | Purpose |
| ---- | ------- |
| `frontend/.../skriptoteketGhostText.ts` | Ghost text extension |
| `frontend/.../skriptoteketIntelligence.ts` | Bundle integration |
| `frontend/.../useSkriptoteketIntelligenceExtensions.ts` | Config composable |

---

## 11. Testing

### 11.1 Backend

- Unit: Provider formats FIM request correctly
- Unit: System prompt template composes (placeholders resolved, within budget)
- Integration: Endpoint requires auth + CSRF
- Integration: Returns `enabled=false` when disabled
- Integration: Truncated response returns empty completion

### 11.2 Frontend

- Unit: Ghost text displays at cursor position
- Unit: Multi-line ghost text preserves indentation/newlines
- Unit: Tab accepts, Escape dismisses
- Unit: Document change clears ghost text
- E2E: Full flow with mock LLM server

---

## 12. References

- [ADR-0043: AI completion integration](../adr/adr-0043-ai-completion-integration.md)
- [ADR-0050: Self-hosted LLM infrastructure](../adr/adr-0050-self-hosted-llm-infrastructure.md)
- [ADR-0035: Script editor intelligence architecture](../adr/adr-0035-script-editor-intelligence-architecture.md)
- [ref-ai-script-generation-kb.md](ref-ai-script-generation-kb.md) - Full knowledge base
- [Tabby Config.toml](https://tabby.tabbyml.com/docs/administration/config-toml/) - Tabby configuration
- [Tabby Code Completion](https://tabby.tabbyml.com/docs/administration/code-completion/) - Tabby settings
