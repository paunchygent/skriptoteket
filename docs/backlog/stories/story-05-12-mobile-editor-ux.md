---
type: story
id: ST-05-12
title: "Mobile editor UX: iOS file upload, CodeMirror ordering, width overflow, nav overlay"
status: in_progress
owners: "agents"
created: 2025-12-19
epic: "EPIC-05"
acceptance_criteria:
  - "Given iOS Safari, when user taps 'Välj fil' on tool run page, then file picker opens without 'Åtgärden tillåts inte' error"
  - "Given mobile viewport (<1024px), when Testyta loads, then KÄLLKOD (CodeMirror) appears at top with min 40vh height (~15-20 lines visible), and REDIGERING sidebar appears below"
  - "Given mobile viewport, when navigating between Testyta panels, then viewport width stays within screen bounds (no horizontal scroll)"
  - "Given mobile viewport, when hamburger menu opens in Testyta, then dropdown overlays content cleanly without compressing editor panels"
  - "Given mobile viewport, the editor page scrolls vertically to accommodate expanded CodeMirror + sidebar without excessive internal scrolling"
---

## Context

Four mobile UX issues were discovered during ST-05-11 verification:

1. **iOS file upload blocked** - iOS shows "Åtgärden tillåts inte" (Action not allowed) when trying to upload files
2. **Wrong section ordering** - Metadata sidebar appears first on mobile, but CodeMirror should be first
3. **Width overflow** - After navigating in Testyta, viewport becomes wider than screen
4. **Mobile nav collapses content** - Hamburger dropdown pushes and compresses editor content instead of overlaying

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

**Symptom:** After navigating between Testyta panels, viewport becomes wider than screen, persists after leaving page.

**Root cause:** CodeMirror calculates its width before mobile CSS applies. No explicit `max-width: 100vw` constraint prevents it from expanding beyond viewport.

**File affected:** `src/skriptoteket/web/static/css/app/editor.css` (mobile media query)

### Issue 4: Mobile Nav Collapses Content

**Symptom:** When hamburger dropdown opens in Testyta, the editor content (Skripteditorn card, run_tool) is visible and awkwardly compressed underneath the dropdown.

**Root cause:** Mobile nav (`.huleedu-mobile-nav`) has no positioning - it's in document flow between header and main. When expanded, it pushes flex children causing compression artifacts in editor layout.

**Files affected:**
- `src/skriptoteket/web/static/css/app/components.css:447` (mobile nav positioning)
- `src/skriptoteket/web/static/css/app/layout.css` (header relative positioning)

### Issue 5: Mobile Editor Clipped / No Vertical Scroll

**Symptom:** On mobile (<1024px), CodeMirror shows only a few lines and the editor+sidebar content is clipped instead of scrollable.

**Root cause:** Desktop containment rules (`height: 100%` + `overflow: hidden`) still apply to key editor containers (e.g. `.huleedu-editor-main`, `.huleedu-editor-code-card`, `.huleedu-editor-form`, `.huleedu-editor-sidebar`). The existing mobile overrides do not override these properties effectively, so CodeMirror can still be clipped even when it has a `min-height`.

**Files affected:** `src/skriptoteket/web/static/css/app/editor.css`

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

### Fix 4: Mobile Nav Overlay
Make mobile nav overlay content with absolute positioning:

```css
/* components.css - update .huleedu-mobile-nav (~line 447) */
.huleedu-mobile-nav {
  display: none;
  flex-direction: column;
  padding: var(--huleedu-space-4);
  background-color: var(--huleedu-canvas);
  border-bottom: var(--huleedu-border-width) solid var(--huleedu-navy-20);
  /* Add overlay positioning */
  position: absolute;
  top: 100%;  /* Below header */
  left: 0;
  right: 0;
  z-index: 100;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
```

Also add header relative positioning for `top: 100%` to work:

```css
/* layout.css - in @media (max-width: 767px) */
.huleedu-header {
  position: relative;
}
```

### Fix 5: Mobile Editor Vertical Growth (Editor-scoped)
Prefer an editor-scoped change over altering the global frame (`.huleedu-frame`).

Override the remaining desktop containment rules on mobile so stacked editor sections can grow naturally and the page can scroll:

```css
/* editor.css, on mobile */
@media (max-width: 1024px) {
  /* Avoid flex sizing clamping stacked panels to viewport height */
  .huleedu-editor-page { display: block; height: auto; min-height: 100vh; }

  /* Let editor sections grow naturally */
  .huleedu-editor-layout { display: flex; flex-direction: column; }
  .huleedu-editor-main,
  .huleedu-editor-sidebar,
  .huleedu-editor-code-card,
  .huleedu-editor-form { height: auto; overflow: visible; }

  /* Ensure CodeMirror has stable visible height */
  .huleedu-editor-textarea-wrapper { height: clamp(350px, 40vh, 520px); }
  .huleedu-editor-textarea-wrapper .CodeMirror { height: 100% !important; min-height: 100% !important; }

  /* Prevent file input + run button layout overflow */
  .huleedu-editor-run-form { flex-wrap: wrap; }
  .huleedu-editor-file-field { flex: 1 1 100%; max-width: none; }
  .huleedu-editor-run-form button[type="submit"] { width: 100%; }
}
```

## Files to Modify

```text
src/skriptoteket/web/templates/tools/run.html           # Add accept="*/*"
src/skriptoteket/web/templates/admin/script_editor.html # Add accept="*/*"
src/skriptoteket/web/static/css/app/editor.css          # Fix order + overflow
src/skriptoteket/web/static/css/app/components.css      # Mobile nav overlay
src/skriptoteket/web/static/css/app/layout.css          # Header relative positioning
```

## Testing

1. **iOS file upload:** Open https://skriptoteket.hule.education on iOS Safari, navigate to a tool, tap "Välj fil" - should open file picker without error
2. **CodeMirror ordering:** Open Testyta on mobile viewport (<1024px) - CodeMirror should appear first, metadata below
3. **Width overflow:** Navigate between Testyta panels on mobile - no horizontal scroll should appear
4. **Mobile nav overlay:** Open hamburger in Testyta - dropdown should overlay content, not compress it
5. **CodeMirror height + scroll:** Open Testyta on mobile - CodeMirror shows ~15-20 lines and page scrolls vertically to reach full editor + sidebar

## Notes

- `accept="*/*"` chosen over specific MIME types to support future tools with different file requirements
- Mobile nav uses `position: absolute` relative to header, not `fixed`, to scroll with page

## Resolution (2025-12-19)

All issues resolved in commit `424e90b`.

### Root Cause
All three issues traced to a single CSS bug: `.huleedu-mobile-nav` had `position: absolute` but **no `top` value**. Without `top`, the browser used `top: auto`, positioning the element at its natural flow location - not truly removing it from document flow.

### Fix Applied
Added `top: var(--huleedu-header-height)` to `.huleedu-mobile-nav` in `components.css`:

```css
.huleedu-mobile-nav {
  position: absolute;
  top: var(--huleedu-header-height);  /* 4rem/64px - positions below header */
  left: 0;
  right: 0;
  z-index: 100;
}
```

### Verification (Puppeteer 375x667 mobile viewport)
- Nav top (65px) matches header bottom (65px) - properly positioned below header
- Nav overlays main content without compressing it
- "KATALOG" fully visible (left edge 17px, within viewport)
- X close icon visible
- No horizontal overflow (document width = viewport width = 375px)
