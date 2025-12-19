# Review Task: Mobile/Touch Screen Compatibility Planning

**Reviewer:** Lead Architect  
**Created:** 2025-12-18  
**Status:** Awaiting Review  

---

## Summary

This review covers the planning artifacts for adding mobile/touch screen compatibility to Skriptoteket. The work addresses three critical usability issues identified on smaller screens.

## Artifacts to Review

### 1. ADR-0020: Responsive Mobile Adaptation Strategy

**File:** `docs/adr/adr-0020-responsive-mobile-adaptation.md`

**Review focus:**
- [ ] Is the "adaptive mobile" (Option A) strategy appropriate given the teacher-centric desktop user base?
- [ ] Are the breakpoint values sensible (`640px`, `768px`, `1024px`)?
- [ ] Is the rejection of mobile-first rewrite (Option B) adequately justified?
- [ ] Are there missing consequences or risks?

### 2. EPIC-05 Updates

**File:** `docs/backlog/epics/epic-05-huleedu-design-harmonization.md`

**Changes made:**
- Status changed from `done` → `in_progress`
- Added scope item: "Responsive/mobile adaptation"
- Added ADR-0020 to dependencies
- Linked three new stories (ST-05-08, ST-05-09, ST-05-10)

**Review focus:**
- [ ] Is reopening EPIC-05 appropriate, or should this be a new epic?
- [ ] Are the new stories correctly scoped under design harmonization?

### 3. Skeleton Stories

| Story | File | Effort Est. |
|-------|------|-------------|
| ST-05-08 | `docs/backlog/stories/story-05-08-responsive-header.md` | Medium |
| ST-05-09 | `docs/backlog/stories/story-05-09-codemirror-mobile-floor.md` | Small |
| ST-05-10 | `docs/backlog/stories/story-05-10-editor-layout-mobile.md` | Medium |

**Review focus:**
- [ ] Are acceptance criteria testable and sufficient?
- [ ] Is the proposed execution order correct (ST-05-09 → ST-05-10 → ST-05-08)?
- [ ] Are task breakdowns appropriate for implementation?
- [ ] Any missing edge cases or considerations?

---

## Technical Decisions Requiring Validation

### Header Navigation (ST-05-08)

**Proposal:** Hamburger menu with JS toggle at `<768px`

**Questions for reviewer:**
1. Should the mobile nav be a slide-out panel or dropdown?
2. Is ~20 LOC JS acceptable, or should we explore CSS-only `:target` approach?
3. Should we add `aria-expanded`/`aria-controls` as required or nice-to-have?

### CodeMirror Floor (ST-05-09)

**Proposal:** `min-height: 250px` on wrapper

**Questions for reviewer:**
1. Is 250px the right floor value (approx 10-12 lines)?
2. Should we consider a "read-only on mobile" pattern for future iteration?

### Editor Layout (ST-05-10)

**Proposal:** CSS `order: -1` to move sidebar above main content on mobile

**Questions for reviewer:**
1. Is order swap sufficient, or do we need collapsible accordion sections?
2. Should Save button be sticky-positioned on mobile?
3. Is 44×44px touch target audit blocking or nice-to-have?

---

## Root Cause Analysis Reference

The original analysis identified these root causes:

| Issue | Root Cause | Proposed Fix |
|-------|-----------|--------------|
| Header cut off | `flex-wrap: nowrap` + no breakpoint | Hamburger menu |
| CodeMirror collapse | `min-height: 0` + flex shrink | Height floor |
| Testyta columns broken | Fixed 320px sidebar | Grid reorder |

---

## Approval Criteria

- [ ] ADR-0020 status can be changed to `accepted`
- [ ] Story acceptance criteria are approved
- [ ] Technical approach for each story is validated
- [ ] Execution order is confirmed

---

## Next Steps After Approval

1. Begin implementation with ST-05-09 (smallest, immediate impact)
2. Live-test each story on device emulator at 320px, 375px, 768px, 1024px
3. Record verification in `.agent/handoff.md` per session rule
