---
type: epic
id: EPIC-05
title: "HuleEdu design system harmonization"
status: proposed
owners: "agents"
created: 2025-12-15
outcome: "Skriptoteket frontend uses HuleEdu design tokens and Brutalist styling, ensuring visual consistency for future HuleEdu integration."
---

## Scope

This epic applies the HuleEdu design system across all Skriptoteket web templates:

- **Design tokens integration**: CSS custom properties for colors, typography, spacing, shadows
- **Template migration**: Update all templates to use HuleEdu component classes
- **HTMX UX enhancements**: Loading states, toast notifications, form improvements (per REF-htmx-ux-enhancement-plan)
- **CodeMirror theming**: Style code editor to match design language

## Stories

### ST-05-01: CSS foundation and base template

- Add HuleEdu design tokens to `static/css/huleedu-design-tokens.css`
- Create `static/css/app.css` with application extensions
- Update `base.html`: Google Fonts, CSS link, ledger frame, toast container, grid background
- Configure `hx-boost` for SPA-like navigation

**Acceptance criteria**:

- Given the app loads, when viewing any page, then canvas background and IBM Plex fonts are visible
- Given the viewport is >= 768px, when viewing the page, then ledger frame border is visible with margin
- Given the app loads, when inspecting CSS, then HuleEdu design tokens are available as custom properties

### ST-05-02: Simple template migration (login, home, error)

- Convert `login.html` to use HuleEdu card, input, and button classes
- Convert `home.html` to use HuleEdu card and link classes
- Convert `error.html` to use HuleEdu styling with burgundy accent

**Acceptance criteria**:

- Given the login page loads, when viewing the form, then it displays with brutal shadow card and styled inputs
- Given a login error occurs, when viewing the page, then error message displays in burgundy text

### ST-05-03: Browse template migration

- Convert `browse_professions.html` to use HuleEdu list/row classes
- Convert `browse_categories.html` to use HuleEdu list/row classes
- Convert `browse_tools.html` to use HuleEdu list/row classes
- Add arrow indicators to navigation links

**Acceptance criteria**:

- Given the browse page loads, when hovering a list item, then background highlights with navy-02
- Given a list item is hovered, when viewing the arrow, then it turns burgundy

### ST-05-04: Suggestion template migration

- Convert `suggestions_new.html` to use HuleEdu form styling
- Replace `<br>` checkbox layout with flex checkbox groups
- Convert `suggestions_review_queue.html` with status dots
- Convert `suggestions_review_detail.html` with labels, form groups, decision history styling

**Acceptance criteria**:

- Given the suggestion form loads, when viewing checkboxes, then they display as flex-wrap items
- Given the review queue loads, when viewing a suggestion, then appropriate status dot color is visible

### ST-05-05: Admin template migration

- Convert `admin_tools.html` with button hierarchy (publish=burgundy, depublish=outline)
- Convert `admin/script_editor.html` with editor layout, tabs, pills
- Convert `admin/partials/version_list.html` with row styling
- Convert `admin/partials/run_result.html` with card and status badges
- Apply CodeMirror theme overrides

**Acceptance criteria**:

- Given the tools list loads, when viewing publish button, then it displays in burgundy
- Given the script editor loads, when viewing CodeMirror, then it uses canvas background and navy border
- Given a sandbox run completes, when viewing results, then they display in a brutal shadow card

### ST-05-06: HTMX loading and toast enhancements

- Add toast partial `templates/partials/toast.html`
- Implement OOB swap for toast notifications
- Add loading spinners to form buttons
- Test graceful degradation (forms work without JS)

**Acceptance criteria**:

- Given a form submits, when in progress, then spinner displays next to button text
- Given a successful action, when toast appears, then it slides in from right with navy background
- Given JavaScript is disabled, when submitting a form, then it still works via full page reload

## Risks

- Design token updates in HuleEdu may require Skriptoteket updates (mitigate: version tokens file)
- Google Fonts CDN dependency (mitigate: fallback to system fonts in font stack)
- Template migration may reveal inconsistent markup patterns (mitigate: standardize during migration)

## Dependencies

- ADR-0001 (server-driven HTMX UI approach)
- ADR-0017 (HuleEdu design system adoption)
- REF-htmx-ux-enhancement-plan (implementation guide)
- EPIC-04 ST-04-03 (admin script editor - already exists, styling applied here)
