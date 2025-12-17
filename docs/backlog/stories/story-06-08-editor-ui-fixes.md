---
type: story
id: ST-06-08
title: "Fix script editor UI issues (file input, CodeMirror scroll)"
status: ready
owners: "agents"
created: 2025-12-17
epic: "EPIC-06"
acceptance_criteria:
  - "File input shows only custom 'Välj fil' button, native input is hidden"
  - "CodeMirror loads and initializes on first page visit (no reload required)"
  - "Code panel scrolls correctly within its container"
  - "Editor dynamically resizes when browser window is resized"
  - "Toolbar (Välj fil, Testkör, version badges) stays visible at bottom of code card"
  - "Other pages (Katalog, Mina verktyg, etc.) retain normal scroll behavior"
---

## Context

The script editor (`/admin/tools/{tool_id}`) has several UI bugs that need fixing.

### Issue 1: File Input Shows Twice

**Location**: `src/skriptoteket/web/templates/admin/script_editor.html` lines 76-82

The native file input is visible alongside the custom styled "Välj fil" button. The CSS hiding
technique isn't working properly.

**Current HTML**:
```html
<label class="huleedu-file-label">
  <span class="huleedu-file-fake-button">Välj fil</span>
  <input type="file" name="file" class="huleedu-file-hidden" ... />
</label>
```

**Current CSS** (`app.css`):
```css
.huleedu-file-hidden {
  position: absolute;
  height: 0;
  width: 0;
  padding: 0;
  margin: 0;
  border: 0;
  opacity: 0;
  overflow: hidden;
  appearance: none;
}
```

**Expected**: Native file input should be completely invisible. Only the styled button shows.

**Investigation needed**: Check if the CSS is being applied correctly, or if there's a specificity
issue. May need to add `clip: rect(0,0,0,0)` or use the visually-hidden pattern.

### Issue 2: CodeMirror Initialization Timing

**Location**: `src/skriptoteket/web/templates/admin/script_editor.html` lines 187-225

**Symptoms**:
- First visit to editor page: CodeMirror doesn't load, textarea shows plain text
- After page reload: CodeMirror initializes, syntax highlighting works
- This suggests the deferred script loading or DOMContentLoaded timing is wrong

**Current JS**:
```javascript
<script src="/static/vendor/codemirror/codemirror.min.js" defer></script>
<script src="/static/vendor/codemirror/mode/python/python.min.js" defer></script>
<script>
  (function () {
    var initialized = false;
    function init() {
      if (initialized) return;
      if (!window.CodeMirror) return;  // <-- This check fails on first load?
      ...
    }
    document.addEventListener("DOMContentLoaded", init);
    window.addEventListener("load", init);
  })();
</script>
```

**Investigation needed**:
- The `defer` attribute may cause scripts to load after `DOMContentLoaded` fires
- HTMX navigation (hx-boost) may not re-execute deferred scripts
- Consider using `load` event only, or checking CodeMirror availability in a loop/timeout

### Issue 3: Code Panel Scroll and Viewport Fill

**Location**: `src/skriptoteket/web/static/css/app.css` (SCRIPT EDITOR LAYOUT section)

**Symptoms**:
- Code panel doesn't scroll properly within its container
- Editor doesn't dynamically resize when window is resized
- Toolbar (Välj fil, Testkör) gets pushed off-screen on smaller viewports

**Root cause analysis**:
The editor layout uses a two-column CSS grid. The left column contains the code card with:
- Form with "Källkod" label
- Textarea wrapper (replaced by CodeMirror)
- Toolbar at bottom

The challenge is making the code panel fill available viewport space while:
1. Keeping toolbar visible at bottom
2. Not breaking scroll on other pages (body overflow: hidden breaks HTMX navigation)
3. Allowing CodeMirror to scroll internally

**Attempted solutions that failed**:
- `overflow: hidden` on body/frame: Breaks scroll on all pages
- CSS `:has()` selector for page-specific styles: Same problem with HTMX body class persistence
- `calc(100vh - Npx)` on wrapper: Static offset doesn't account for dynamic header sizes
- JavaScript height calculation: Unreliable on resize

**Recommended approach**:
Research how VS Code web, Monaco editor, or GitHub's code editor handle this. They typically
use position: absolute/fixed for the editor panel, taking it out of document flow entirely.

## Files to Modify

- `src/skriptoteket/web/static/css/app.css` - File input hiding, editor layout
- `src/skriptoteket/web/templates/admin/script_editor.html` - CodeMirror init timing
- Possibly `src/skriptoteket/web/templates/base.html` - If page-specific body classes needed

## Testing

1. Navigate to `/admin/tools/{any-tool-id}` via direct URL (not HTMX navigation)
2. Verify CodeMirror loads with syntax highlighting on first visit
3. Verify only one "Välj fil" button is visible
4. Resize browser window - editor should adapt, toolbar should stay visible
5. Navigate to other pages - verify normal scroll works
6. Test on multiple viewport sizes (desktop, tablet breakpoint)
