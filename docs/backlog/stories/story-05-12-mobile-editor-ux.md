---
type: story
id: ST-05-12
title: "Mobile editor UX: iOS file upload, CodeMirror ordering, width overflow"
status: ready
owners: "agents"
created: 2025-12-19
epic: "EPIC-05"
acceptance_criteria:
  - "Given iOS Safari, when user taps 'Välj fil' on tool run page, then file picker opens without 'Åtgärden tillåts inte' error"
  - "Given mobile viewport (<1024px), when Testyta loads, then CodeMirror editor appears at top and metadata sidebar appears below"
  - "Given mobile viewport, when navigating between Testyta panels, then viewport width stays within screen bounds (no horizontal scroll)"
---

## Context

Three mobile UX issues were discovered during ST-05-11 verification:

1. **iOS file upload blocked** - iOS shows "Åtgärden tillåts inte" (Action not allowed) when trying to upload files
2. **Wrong section ordering** - Metadata sidebar appears first on mobile, but CodeMirror should be first
3. **Width overflow** - After navigating in Testyta, viewport becomes wider than screen

## Root Cause Analysis

### Issue 1: iOS File Upload

**Symptom:** iOS Safari rejects file picker with organization permission error.

**Root cause:** Missing `accept` attribute on `<input type="file">`. iOS is stricter than desktop browsers about file picker permissions when no explicit MIME types are specified.

**Files affected:**
- `src/skriptoteket/web/templates/tools/run.html:31`
- `src/skriptoteket/web/templates/admin/script_editor.html:73`

### Issue 2: CodeMirror Ordering

**Symptom:** On mobile (<1024px), metadata sidebar appears first, CodeMirror at bottom.

**Root cause:** CSS `order: -1` on `.huleedu-editor-sidebar` in mobile media query makes sidebar appear first.

**File affected:** `src/skriptoteket/web/static/css/app/editor.css:76`

### Issue 3: Width Overflow

**Symptom:** After navigating between Testyta panels, viewport becomes wider than screen, persists after leaving page. Hamburger menu causes ugly panel collapse.

**Root cause:** CodeMirror calculates its width before mobile CSS applies. No explicit `max-width: 100vw` constraint prevents it from expanding beyond viewport.

**File affected:** `src/skriptoteket/web/static/css/app/editor.css` (mobile media query)

## Implementation Plan

### Fix 1: iOS File Upload
Add `accept="*/*"` attribute to file inputs:

```html
<!-- tools/run.html:31 -->
<input type="file" ... accept="*/*" />

<!-- admin/script_editor.html:73 -->
<input type="file" ... accept="*/*" />
```

### Fix 2: CodeMirror Ordering
Remove `order: -1` from sidebar in mobile media query (natural HTML order puts CodeMirror first):

```css
/* editor.css, in @media (max-width: 1024px) */
.huleedu-editor-sidebar {
  /* Remove: order: -1; */
  width: 100%;
  max-width: none;
  height: auto;
  max-height: 40vh;
  overflow-y: auto;
}
```

### Fix 3: Width Overflow
Add explicit width constraints in mobile media query:

```css
/* editor.css, in @media (max-width: 1024px) */
.huleedu-editor-main,
.huleedu-editor-code-card,
.huleedu-editor-form,
.huleedu-editor-textarea-wrapper {
  max-width: 100vw;
  overflow-x: hidden;
}

.CodeMirror {
  max-width: 100% !important;
}
```

## Files to Modify

```text
src/skriptoteket/web/templates/tools/run.html           # Add accept="*/*"
src/skriptoteket/web/templates/admin/script_editor.html # Add accept="*/*"
src/skriptoteket/web/static/css/app/editor.css          # Fix order + overflow
```

## Testing

1. **iOS file upload:** Open https://skriptoteket.hule.education on iOS Safari, navigate to a tool, tap "Välj fil" - should open file picker without error
2. **CodeMirror ordering:** Open Testyta on mobile viewport - CodeMirror should appear first
3. **Width overflow:** Navigate between Testyta panels on mobile - no horizontal scroll should appear

## Notes

- `accept="*/*"` chosen over specific MIME types to support future tools with different file requirements
- Hamburger panel collapse on mobile is a cosmetic issue that will improve with width overflow fix
