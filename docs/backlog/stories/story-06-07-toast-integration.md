---
type: story
id: ST-06-07
title: "Integrate toast notifications into admin workflows"
status: ready
owners: "agents"
created: 2025-12-16
epic: "EPIC-06"
acceptance_criteria:
  - "Metadata save shows success toast instead of full page reload"
  - "Suggestion decisions show toast feedback"
  - "Version workflow actions (submit/publish/request-changes) show toasts"
  - "Error scenarios show error toasts (type: error)"
  - "All toasts auto-dismiss after 12 seconds (default)"
  - "Manual tests confirm toast appears and dismisses correctly"
---

## Context

ST-05-06 created toast infrastructure (partial, CSS, auto-dismiss JS) but never integrated
it into any routes. Toast feedback improves UX by avoiding full page reloads for simple
confirmations.

### Existing Infrastructure

- **Toast partial**: `src/skriptoteket/web/templates/partials/toast.html`
- **Toast container**: `<div id="toast-container">` in `base.html`
- **Auto-dismiss + replace JS**: `src/skriptoteket/web/static/js/app.js` (single-toast fade replace on `htmx:oobBeforeSwap`)
- **CSS**: Toast styles in `src/skriptoteket/web/static/css/app/components.css`

### OOB Swap Pattern

```html
<div class="huleedu-toast huleedu-toast-{{ type }}"
     hx-swap-oob="innerHTML:#toast-container"
     data-auto-dismiss="12000">
```

## Routes to Integrate

| Route | File | Toast Message |
|-------|------|---------------|
| `/admin/tools/{tool_id}/metadata` | admin_scripting.py:118 | "Metadata sparad" |
| `/admin/tool-versions/{version_id}/submit-review` | admin_scripting.py:384 | "Skickad for granskning" |
| `/admin/tool-versions/{version_id}/publish` | admin_scripting.py:423 | "Version publicerad" |
| `/admin/tool-versions/{version_id}/request-changes` | admin_scripting.py:462 | "Andringar begarda" |
| `/admin/tool-versions/{version_id}/rollback` | admin_scripting.py:618 | "Aterstald till v{n}" |
| `/admin/suggestions/{suggestion_id}/decision` | suggestions.py:220 | "Forslag godkant/nekat" |

## Plan

1. Create helper function to return toast response for HTMX requests
2. Update metadata save route to return toast on success
3. Update suggestion decision route to return toast
4. Update version workflow routes (submit-review, publish, request-changes, rollback)
5. Test manually across all integrated routes
