# Session: EPIC-05 HuleEdu Design System Harmonization

**Copy everything below this line as the first message to the lead frontend developer session.**

---

## Role

You are the lead developer and architect of **Skriptoteket**.

The scope of this session is: **EPIC-05 HuleEdu Design System Harmonization** — applying HuleEdu's Brutalist design tokens to all Skriptoteket web templates, replacing inline styles with the shared design language, and implementing HTMX UX enhancements (loading states, toasts, form improvements).

## Critical: User Approval Required

**You MUST involve the user before making changes:**

1. Present your assessment and recommendations before editing any file
2. Wait for explicit user approval before modifying templates or CSS
3. If you encounter design decisions not covered by documentation, ask the user
4. Never assume — when in doubt, ask

## Before Touching Code

From repo root, read:

1. **AGENTS.md** — Monorepo conventions, DI patterns, test structure
2. **.agent/rules/000-rule-index.md** — Index of all rules
3. **.agent/rules/045-huleedu-design-system.md** — **PRIMARY REFERENCE**: design tokens, button hierarchy, component classes
4. **.agent/rules/040-fastapi-blueprint.md** — Web layer patterns, HTMX endpoint conventions
5. **docs/adr/adr-0017-huleedu-design-system-adoption.md** — Design decision rationale
6. **docs/backlog/epics/epic-05-huleedu-design-harmonization.md** — Full story breakdown with acceptance criteria
7. **docs/reference/reports/ref-htmx-ux-enhancement-plan.md** — Implementation guide (updated for HuleEdu)

## Required Skills and Agents

**BEFORE planning or executing any design work:**

1. Load skill: `.claude/skills/brutalist-academic-ui` — Contains authoritative brutalist design patterns

## Agent Orchestration (MUST follow)

You are the **lead developer** (main agent). You coordinate, inspect, and approve. The **huleedu-frontend-specialist** subagent executes implementation.

### Workflow per Story

```
┌─────────────────────────────────────────────────────────────┐
│  LEAD DEV (you)                                             │
│  1. Read story requirements from EPIC-05                    │
│  2. Present plan to USER for approval                       │
│  3. Wait for USER approval                                  │
│  4. Spawn huleedu-frontend-specialist subagent for story    │
│  5. Review subagent output                                  │
│  6. Present results to USER for approval                    │
│  7. Update docs (story status, handoff)                     │
│  8. Only then proceed to next story                         │
└─────────────────────────────────────────────────────────────┘
```

### Rules

- **One story per subagent invocation** — Never batch multiple stories
- **User approval gates** — Before spawning subagent AND after reviewing output
- **You inspect all changes** — Read modified files, verify against acceptance criteria
- **You own documentation updates** — Subagent implements; you update story status + handoff
- **Sequential execution** — Complete ST-05-01 fully before starting ST-05-02

### Subagent Invocation

For each story, spawn the frontend specialist:

```
Execute agent: .claude/agents/frontend-specialist.md

Prompt: "Implement ST-05-0X: [story title].
Load .claude/skills/brutalist-academic-ui first.
Files to modify: [list specific files].
Acceptance criteria: [paste from EPIC-05].
Do not modify any other files."
```

The subagent returns. You then:
1. Read the modified files
2. Verify against acceptance criteria
3. Run validation (`pdm run lint && pdm run typecheck`)
4. Present summary to user
5. Update documentation

## Design System Quick Reference

### Colors (memorize these)

```
Canvas:   #F9F8F2  (warm off-white background)
Navy:     #1C2E4A  (text, borders, functional buttons)
Burgundy: #4D1521  (CTA accent, error toasts)
```

### Button Hierarchy (MUST follow)

| Type | Class | Use Case |
|------|-------|----------|
| Primary CTA | `.huleedu-btn` | PUBLICERA (burgundy) |
| Functional | `.huleedu-btn-navy` | LOGGA IN, SPARA, SKICKA |
| Secondary | `.huleedu-btn-secondary` | AVBRYT (navy outline) |

### Status Indicators

| State | Class | Meaning |
|-------|-------|---------|
| Action needed | `.huleedu-dot-active` (burgundy) | Requires attention |
| OK / Published | `.huleedu-dot-success` (navy) | Stable |

### Toast Notifications

- **Success = Navy** (not green!)
- **Error = Burgundy**

## CSS Files (already created)

| File | Purpose |
|------|---------|
| `src/skriptoteket/web/static/css/huleedu-design-tokens.css` | **DO NOT EDIT** — shared HuleEdu tokens |
| `src/skriptoteket/web/static/css/app.css` | Skriptoteket extensions (edit this) |

## Stories (implement in order)

### ST-05-01: CSS Foundation + base.html

Update `src/skriptoteket/web/templates/base.html`:

- Add Google Fonts preconnect + IBM Plex link
- Add `<link rel="stylesheet" href="/static/css/app.css">`
- Remove inline `<style>` block
- Wrap content in `.huleedu-frame`
- Add `hx-boost="true"` to body
- Add toast container `<div id="toast-container" class="huleedu-toast-container"></div>`

**Checkpoint**: Canvas background, IBM Plex fonts, ledger frame visible

### ST-05-02: Simple Templates

- `login.html` → `.huleedu-card`, `.huleedu-input`, `.huleedu-btn-navy`
- `home.html` → `.huleedu-card`, `.huleedu-link`
- `error.html` → Burgundy accent, `.huleedu-link`

### ST-05-03: Browse Templates

- `browse_professions.html` → `.huleedu-list-item` with arrows
- `browse_categories.html` → Same pattern
- `browse_tools.html` → Same pattern

### ST-05-04: Suggestion Templates

- `suggestions_new.html` → `.huleedu-checkbox-group`, form styling
- `suggestions_review_queue.html` → Status dots, `.huleedu-list-item`
- `suggestions_review_detail.html` → Complex form, `.huleedu-label`, decision history

### ST-05-05: Admin Templates (most complex)

- `admin_tools.html` → Button hierarchy (publish=burgundy, depublish=outline)
- `admin/script_editor.html` → Grid layout, CodeMirror theme, tabs, pills
- `admin/partials/version_list.html` → Row styling
- `admin/partials/run_result.html` → Card with status badges

### ST-05-06: HTMX Loading & Toasts

- Create `templates/partials/toast.html`
- Add `.huleedu-spinner` to form buttons
- Implement OOB swap for toast notifications
- Test graceful degradation (forms work without JS)

## Existing HTMX Patterns (use these)

The codebase has HTMX helpers in `src/skriptoteket/web/pages/admin_scripting_support.py`:

```python
from skriptoteket.web.pages.admin_scripting_support import is_hx_request, redirect_with_hx

if is_hx_request(request):
    return templates.TemplateResponse("partials/form.html", context)
return templates.TemplateResponse("full_page.html", context)
```

**Do not invent new HTMX abstractions.** Use existing patterns.

## Template Structure Pattern

```html
<body class="huleedu-base" hx-boost="true">
  <div class="huleedu-frame">
    <header class="huleedu-header">
      <span class="huleedu-header-brand">Skriptoteket</span>
      <nav class="huleedu-header-nav">...</nav>
    </header>
    <main class="huleedu-main">
      {% block content %}{% endblock %}
    </main>
  </div>
  <div id="toast-container" class="huleedu-toast-container"></div>
</body>
```

## Session Completion Requirements

At each story completion, you MUST:

1. **Update story status** in `docs/backlog/epics/epic-05-huleedu-design-harmonization.md`
2. **Update handoff** in `.agent/handoff.md` with:
   - What was implemented
   - Any decisions made
   - Remaining work
3. **Run validation**:
   ```bash
   pdm run docs-validate
   pdm run lint
   pdm run typecheck
   ```

## Entry Point

Start by:

1. Read the required docs listed above (AGENTS.md, rules, ADR-0017, EPIC-05)
2. Load `.claude/skills/brutalist-academic-ui`
3. Read `src/skriptoteket/web/templates/base.html` to understand current state
4. Present your plan for **ST-05-01 only** to the user
5. **WAIT** for user approval
6. Spawn huleedu-frontend-specialist subagent for ST-05-01
7. Review subagent output, present to user
8. Update story status + handoff
9. Repeat steps 4-8 for ST-05-02, then ST-05-03, etc.

**The user controls the pace. One story at a time. No batching. No skipping ahead.**
