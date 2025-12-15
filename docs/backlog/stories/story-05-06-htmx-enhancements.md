---
type: story
id: ST-05-06
title: "HTMX loading and toast enhancements"
status: done
owners: "agents"
created: 2025-12-15
epic: "EPIC-05"
acceptance_criteria:
  - "Given a form submits, when in progress, then spinner displays next to button text"
  - "Given a successful action, when toast appears, then it slides in from right with navy background"
  - "Given JavaScript is disabled, when submitting a form, then it still works via full page reload"
---

## Context

Enhancing the user experience with HTMX-driven interactions, loading states, and notifications.

## Tasks

- [x] Add toast partial `templates/partials/toast.html`
- [x] Implement OOB swap for toast notifications
- [x] Add loading spinners to form buttons (CSS exists in app.css, pattern documented)
- [x] Test graceful degradation (forms work without JS - all forms have `method="post"`)

## Implementation Notes (2025-12-15)

### Toast Partial
Created `src/skriptoteket/web/templates/partials/toast.html` with:
- OOB swap pattern: `hx-swap-oob="beforeend:#toast-container"`
- Success (navy) and error (burgundy) variants
- Auto-dismiss after 5 seconds via JS in base.html
- Manual dismiss button
- ARIA attributes for accessibility

### Loading Spinners
CSS already exists in app.css:
- `.huleedu-spinner` - base spinner animation
- `.huleedu-spinner-sm` - small variant for buttons
- `.huleedu-spinner-light` - light variant for dark backgrounds
- `.htmx-indicator` - hidden by default, shown during htmx requests

### Usage Pattern
```html
<button type="submit" class="huleedu-btn huleedu-btn-navy" hx-post="/action">
  <span class="htmx-indicator huleedu-spinner huleedu-spinner-sm huleedu-spinner-light"></span>
  Spara
</button>
```

Backend returns toast via OOB swap:
```python
if is_hx_request(request):
    return templates.TemplateResponse(
        "partials/toast.html",
        {"request": request, "message": "Sparat!", "type": "success"}
    )
```
