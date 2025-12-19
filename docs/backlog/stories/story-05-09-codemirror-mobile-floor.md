---
type: story
id: ST-05-09
title: "CodeMirror minimum height floor"
status: done
owners: "agents"
created: 2025-12-18
epic: "EPIC-05"
acceptance_criteria:
  - "Given script editor on any viewport, when page loads, then CodeMirror has at least 250px visible height"
  - "Given run-result expands, when layout recalculates, then CodeMirror does not shrink below 250px"
  - "Given viewport width ≤1024px, when editor stacks vertically, then CodeMirror remains scrollable and usable"
---

## Context

CodeMirror collapses to near-zero height on mobile because `min-height: 0` allows flex shrink without a floor. The editor becomes invisible or unusable.

## Tasks

- [ ] Add `min-height: 250px` to `.huleedu-editor-textarea-wrapper`
- [ ] Verify CodeMirror internal scroll works correctly with the floor
- [ ] Test on 375px, 768px, 1024px viewports
- [ ] Verify run-result panel doesn't push editor off-screen

## Files to Modify

```text
src/skriptoteket/web/static/css/app/editor.css  # min-height floor
```

## Notes

- 250px is approximately 10-12 lines of code visible – enough to be useful
- The floor prevents collapse but allows growth when space is available
- Consider adding a "read-only" or "expand" pattern for mobile in future iteration
