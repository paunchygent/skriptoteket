---
type: adr
id: ADR-0025
title: "Embedded SPA islands for editor/runtime surfaces"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-19
updated: 2025-12-21
links: ["EPIC-10", "ADR-0022", "ADR-0024"]
---

## Context

Skriptoteket is primarily server-rendered with HTMX. This approach is a good fit for teacher-first, browse/list-heavy
flows and keeps the web layer thin.

However, some surfaces are approaching the complexity boundary of Jinja + HTMX + raw JS/CSS:

- **CodeMirror editor surfaces** (admin/contributor tooling) require robust sizing, interaction state, and rich UX.
- **Multi-turn interactive tool UI** (typed outputs + action forms + persisted state) benefits from a component model,
  client-side state management, and richer UI composition.

We also want to align the frontend stack with HuleEdu for easier future integration.

## Decision

### 1) Keep HTMX/SSR for the broader app

The default UI paradigm remains server-rendered HTML with HTMX enhancements, including browse/list surfaces such as
Testyta and Mina verktyg.

### 2) Allow embedded SPA “islands” for high-complexity surfaces

SPA islands are the approved approach for:

1. **Admin/contributor editors** (tool editor, CodeMirror UX, editor-side interactions).
2. **End-user interactive tool UI** for multi-turn tools and curated apps (rendering typed outputs, action forms, and
   session state).

SPA islands are mounted into server-rendered pages (a root `<div>` plus initial JSON boot payload), and communicate
with the backend via JSON APIs.

### 3) Use the HuleEdu-aligned frontend stack

To maximize integration compatibility, SPA islands use the same stack as HuleEdu:

| Layer      | Technology                                                       |
|------------|------------------------------------------------------------------|
| Framework  | Vue 3.5 (Composition API, `<script setup>`)                      |
| State      | Pinia 3.0                                                        |
| Routing    | vue-router 4.6                                                   |
| Validation | Zod 4.1 (runtime schema validation)                              |
| Build      | Vite 6.0, pnpm 10.17                                             |
| Styling    | TailwindCSS 4.1 (HuleEdu tokens, brutalist design system)        |
| TypeScript | 5.7 (strict mode, vue-tsc)                                       |
| Testing    | Vitest 4.0, @vue/test-utils, jsdom                               |
| Linting    | ESLint 9 (flat config) with typescript-eslint, eslint-plugin-vue |

### 4) Backend-first contract and API surface

SPA islands are enabled by a backend-first foundation:

- Tool UI contract v2 (`outputs[]`, `next_actions[]`, `state`) (ADR-0022).
- Minimal API surface for turn-taking and replay (`start_action`, `get_session_state`, `get_run`, `list_artifacts`)
  (ADR-0024).
- A deterministic app-side normalizer enforcing allowlists and size budgets (policy-driven), so UI remains safe and
  consistent across both HTMX pages and SPA islands.

### 5) Coexistence rules with HTMX

To prevent HTMX from interfering with the SPA island:

- Wrap the SPA mount root in a container with `hx-boost="false"`.
- Do not target the SPA root with HTMX swaps (`hx-target` must not point inside the SPA root).
- SPA internal navigation and form interactions must be handled entirely by Vue.
- HTMX may remain enabled globally for the rest of the page/site.

### 6) Build and asset integration

- SPA assets are built by Vite and emitted as static files under the FastAPI `/static` mount.
- Production uses hashed assets + a Vite manifest to generate `<script>`/`<link>` tags from templates.
- Development supports either:
  - building to `/static` on file change, or
  - a Vite dev server with proxying to FastAPI (optional, but preferred for DX).

### 7) Security posture

- Tools must not ship arbitrary UI JavaScript.
- Any HTML output from tools remains sandboxed (`html_sandboxed`), without allowing scripts to execute.
- Interactivity is provided by platform-rendered UI components based on typed outputs and action schemas.

## Consequences

### Benefits

- Preserves the simplicity and maintainability of SSR/HTMX for most pages.
- Enables richer UX where needed (editor/runtime surfaces) without a full SPA rewrite.
- Aligns with HuleEdu frontend technology choices, reducing integration friction.
- Keeps end-user rendering safe via strict contracts, allowlists, and deterministic normalization.

### Tradeoffs / Risks

- Introduces a second frontend toolchain (pnpm/Vite) alongside Python tooling.
- Requires clear boundaries to avoid “two paradigms everywhere”.
- Requires careful CSS isolation to avoid Tailwind/global style conflicts with existing CSS.
