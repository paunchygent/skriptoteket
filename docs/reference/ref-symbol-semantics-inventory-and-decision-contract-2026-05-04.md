---
type: reference
id: REF-symbol-semantics-inventory-and-decision-contract-2026-05-04
title: "Symbol semantics inventory and decision contract"
status: active
owners: "agents"
created: 2026-05-04
updated: 2026-05-04
topic: "symbol-semantics"
links:
  [
    "EPIC-29",
    "ST-29-12",
    "MOCK-st-29-12-symbol-inventory",
    "REF-shared-tool-control-language-v1",
    "REF-frontend-design-system-codemap-2026-03-28",
  ]
---

# Symbol Semantics Inventory and Decision Contract

## Purpose

`ST-29-12` needs a visual and semantic decision surface before more
Klassrumskartan or site-wide icon swaps happen. The goal is to stop treating
symbols as local decoration and instead assign one symbol language to repeated
teacher-facing concepts.

The canonical reasoning artifact is:

- [ST-29-12 symbol inventory HTML](../mockups/st-29-12-symbol-inventory/index.html)
- [HuleEdu Iconify fallback board](../mockups/st-29-12-symbol-inventory/huleedu-iconify-research.html)

## Required Inventory

The inventory must contain:

- every shared icon wrapper exported from
  `frontend/apps/skriptoteket/src/components/icons/`
- every direct `lucide-vue-next` import currently used in relevant SPA surfaces
- the complete locally installed Lucide component inventory available to the
  project
- a seed semantic map showing current assignments, unresolved candidates, and
  known drift
- an Iconify-backed fallback research board for HuleEdu semantic families where
  local Lucide proper may not have an obvious candidate

## Iconify Research Layer Policy

Iconify is approved for `ST-29-12` as a research and indexing layer only. It is
not a design language, not a runtime dependency decision, and not a reason to
mix icon styles before `PR-0292` records explicit semantic choices.

The fallback board must compare:

- `lucide-lab` as the first fallback because it keeps the closest Lucide-family
  visual grammar
- `tabler` as the broader stroke-compatible fallback for EdTech/classroom
  semantics where Lucide and Lucide Lab are weak

The HuleEdu semantic-family inventory must cover classroom, maps,
proximity/short-distance, groups, cooperation, ideation, teacher, hand-in,
bench, homework, exam, grade, learning, assessment, AI, language, and writing.
Runtime implementation order remains Lucide proper first, then Lucide Lab only
if approved, then Tabler only if approved for a specific semantic slot.

## Decision Order

Use this order so the work does not collapse into one-off Klassrumskartan icon
swapping:

1. Global actions and controls:
   create, edit, delete, close, undo, redo, history, overflow, configure,
   download, file type, share link, copy link, search, help, warning, status.
2. Klassrumskartan workspace and domain semantics:
   overview, groups, seating, rules, class list, classroom, students, unassigned
   students, seating place, classroom map, rule map, near teacher, keep near,
   keep apart, smart settings, randomize.
3. Other site/app semantics:
   favorites/bookmarking, catalog/navigation, files/vault, editor tools,
   run/debug affordances, profile/account surfaces.

## Approved Global Action Matrix

These decisions are accepted inputs for `PR-0293` and `PR-0294`.

| Semantic slot | Approved wrapper/component | Approved scope | Rejected/limited use |
|---|---|---|---|
| Create/add | `IconPlus` / `Plus` | Generic create/add action. Visible labels carry the object-specific wording such as `Ny klass`, `Nytt klassrum`, or `Nytt utkast`. | Do not invent object-specific plus variants unless the semantic matrix later approves one. |
| Edit | `IconEdit` / `PencilLine` | Edit an existing object or settings row. | Do not use for create/import. |
| Delete | `IconTrash` / `Trash2` | Destructive deletion only, using the existing danger language. | Do not use burgundy/trash for ordinary remove-from-selection actions unless the action deletes persisted data. |
| Close/dismiss/exit surface | `IconX` / `X` | Close or dismiss a temporary surface; exit the planner shell when the behavior is a close/dismiss action. Default button treatment is compact, low-chrome, and lightly framed on desktop and small screens. | Do not use for delete, logout, or browser-style back navigation. Do not make the default close button a large framed desktop-only affordance. |
| Undo | `IconUndo` / `Undo2` | Undo the previous workspace/editor action. | Do not move to generic history. |
| Redo | `IconRedo` / `Redo2` | Redo the previous undone workspace/editor action. | Do not move to generic history. |
| History | `IconHistory` / `History` | Open previous drafts, versions, or saved snapshots. | Do not use for undo/redo. |
| Overflow menu | `IconMoreVertical` / `MoreVertical` | More actions menu. | Do not use as a semantic substitute for settings. |
| Configure context | `IconAdjustments` -> `SlidersHorizontal` | Contextual control tuning for dense tools and local workspace settings. | Do not use for app-wide settings. |
| App/settings | `IconSettings` / `Settings` | Actual settings/configuration surfaces. | Do not use for rules, local tool tuning, or contextual overflow. |
| Download action | `IconDownload` / `Download` | Save/download action. | Do not use as the file-type symbol. |
| Copy action | new `IconCopy` / `Copy` | Copy text, URL, or generated share value. | Do not use as the share-link source symbol. |
| Actual link/share link | `IconLink2` / `Link2` | Real links, share links, copy-link affordances, and link lists. | Prohibited for relationship/proximity rules such as keep-near. |
| PDF/document file | new `IconFileText` / `FileText` | PDF/document file type. | Do not use as download action. |
| Spreadsheet file | new `IconFileSpreadsheet` / `FileSpreadsheet` | Spreadsheet/Excel file type. | Do not use as download action. |
| Audio file | new `IconFileAudio` / `FileAudio` | Uploaded audio/video source files and transcript-conversion source file affordances. | Do not use as play/run/transcription action; those stay `IconRun` or progress/status surfaces. |
| Search | `IconSearch` / `Search` | Search/filter input affordance. | None. |
| Help | `IconHelp` / `CircleHelp` | Help and guidance entry points. | None. |
| Warning | `IconWarning` / `AlertTriangle` | Warning or risk state. | Do not use for neutral info. |
| Info | `IconInfo` / `Info` | Neutral informational state. | Do not use for warnings. |
| Success/selected | `IconCheck` / `Check` | Selected, confirmed, or success state. | Do not use as a generic bullet when a non-state marker is enough. |
| Blocked/forbidden | `IconBan` / `Ban` | Blocked, unavailable, or forbidden state. | Keep-apart rule usage remains a domain decision, not a global action decision. |

## Approved Klassrumskartan Domain Matrix

These decisions are accepted inputs for `PR-0293`. They cover the planner
workspace/domain symbols and deliberately separate workspace modes from
entities inside those workspaces.

| Semantic slot | Approved wrapper/component | Approved scope | Rejected/limited use |
|---|---|---|---|
| Overview workspace | new `IconOverview` / `LayoutDashboard` | The `Översikt` workspace/mode and dashboard-like planner summary entry points. | Do not reuse `IconClipboardList`; roster/list semantics belong to `Klasslista`. |
| Groups workspace | new `IconGroupsWorkspace` / `tabler:users-group` | The `Grupper` workspace/mode and group-indelning affordance. | Do not use `IconUsersRound`; that remains the student collection symbol. `Group` is rejected as less teacher-readable than `tabler:users-group`. |
| Seating workspace | new `IconSeatingPlan` / `LayoutGrid` | The `Sittplatser` workspace/mode and seating-plan/map affordance. | Do not use `IconArmchair` for the workspace mode; an armchair is an individual seat/place symbol. |
| Individual seat/place | new `IconSeat` or existing `IconArmchair` / `Armchair` | Individual seat/place semantics inside seating surfaces. | Do not use for the whole seating workspace/mode. |
| Rules workspace | new `IconRules` / `ListChecks` | The `Regler` workspace/mode and rule/constraint surfaces. | Reject `IconSettings` because rules are not app settings. Reject `IconPresentation` because it reads as screen/presentation rather than rules. |
| Students | new `IconStudents` or existing `IconUsersRound` / `UsersRound` | Student collection/list semantics such as `Elever` panels. | Do not use for the grouping workspace. |
| Class list | new `IconClassList` / `ClipboardList` | Roster/class-list semantics. | Do not use for generic overview/dashboard after `IconOverview` exists. |
| Classroom | new `IconClassroom` / `tabler:chalkboard-teacher` | Classroom/classroom-template semantics. | Reject `IconSchool` as too broad and reject `Building2` as too generic. This is a named Tabler fallback acceptance, not broad Tabler adoption. |
| Near teacher rule | new `IconTeacherAnchor` / `UserStar` | Rule anchor meaning the selected student should be near the teacher/teacher position. | Reject `IconSchool` and `IconGraduationCap` as too broad for a specific teacher anchor. |
| Keep-near rule | new `IconKeepNear` / `Magnet` | Relationship/proximity rule that keeps selected students close. | `IconLink2` is prohibited because this is not an actual link/share affordance. |
| Keep-apart rule | new `IconKeepApart` or existing `IconBan` / `Ban` | Relationship rule that forbids selected students from being placed near each other. | Reject `Unlink2` because it keeps the link metaphor alive after `IconLink2` was reserved for real links. |

## Approved Other Site/App Matrix

These decisions are accepted inputs for `PR-0294` and may also be implemented
opportunistically in `PR-0293` where touched shared wrappers already serve
Klassrumskartan surfaces.

| Semantic slot | Approved wrapper/component | Approved scope | Rejected/limited use |
|---|---|---|---|
| Favorite/bookmark | `IconBookmark` / `Bookmark` | Favorite/bookmark state in catalog and saved-item surfaces. Filled state means selected favorite. | Do not use for generic save/download. |
| Catalog/library | new `IconCatalog` / `Library` | `Katalog` route, catalog/library navigation, and tool/app browsing surfaces. | Do not use generic list/search symbols for the route identity. |
| Files/vault | new `IconVaultFiles` / `FolderOpen` | `Mina filer`, vault, and file collection/location surfaces. | Do not use file-type icons or `IconDownload` for the vault location. |
| Run action | new `IconRun` / `Play` | Execute, run, or test-run actions such as `Kör` and `Testkör`. | Do not use for run history. |
| Run history | new `IconRunHistory` / `History` | Previous runs, run snapshots, and `Mina körningar`. | Do not use for undo/redo. |
| Debug | new `IconDebug` / `Bug` | Developer/debug diagnostics only. | Do not expose as a normal user-facing help or issue icon. |
| Code/editor surface | new `IconCode` / `Code` | Code editor/tool editor surfaces. | Do not use for generic settings. |
| Profile/account | new `IconProfile` / `CircleUserRound` | Profile/account surfaces. | Do not use for student/person domain symbols. |
| Roles/permissions | new `IconRole` / `ShieldUser` | Role, permission, and access/security semantics. | Do not use for ordinary profile/account. |
| AI feature | new `IconAi` / `Sparkles` | AI capability, AI feature, or AI-assisted behavior. | Use `IconSettings` only for the settings action itself. |
| Loading/spinner | new `IconSpinner` / `LoaderCircle` | Shared loading/progress spinner wrapper. | Direct `LoaderCircle` imports should move behind the wrapper unless a local leaf exception is documented. |
| Password visibility | direct local `Eye` / `EyeOff` allowed | Password field visibility toggle in `AuthPasswordField`. | This is an approved local leaf exception; do not generalize it into a shared semantic wrapper unless repeated elsewhere. |

## PR-0293 Code-Facing Wrapper Map

`PR-0293` should implement these wrapper targets without changing layout,
toolbar priority, workflow behavior, labels, colors, or breakpoint policy.

| Wrapper target | Source icon | Source package | Primary migration target |
|---|---|---|---|
| `IconCopy` | `Copy` | Lucide | Replace direct `Copy` imports in share/link panels. |
| `IconFileText` | `FileText` | Lucide | Replace direct PDF/document file-type imports in export file sections. |
| `IconFileSpreadsheet` | `FileSpreadsheet` | Lucide | Replace direct spreadsheet/Excel file-type imports in export file sections. |
| `IconFileAudio` | `FileAudio` | Lucide | Replace ad hoc uploaded-audio/file glyphs in transcript conversion surfaces. |
| `IconOverview` | `LayoutDashboard` | Lucide | Replace overview mode `IconClipboardList`. |
| `IconGroupsWorkspace` | `users-group` | Tabler | Replace `Grupper` workspace/mode icon. |
| `IconSeatingPlan` | `LayoutGrid` | Lucide | Replace `Sittplatser` workspace/mode icon. |
| `IconRules` | `ListChecks` | Lucide | Replace `Regler` mode `IconSettings`/`IconPresentation`. |
| `IconStudents` | `UsersRound` | Lucide | Student list and `Elever` surfaces; may wrap existing `IconUsersRound` semantics. |
| `IconClassList` | `ClipboardList` | Lucide | `Klasslista` only. |
| `IconClassroom` | `chalkboard-teacher` | Tabler | `Klassrum` and classroom-template surfaces. |
| `IconTeacherAnchor` | `UserStar` | Lucide | Near-teacher rule. |
| `IconKeepNear` | `Magnet` | Lucide | Keep-near relationship/proximity rule. |
| `IconKeepApart` | `Ban` | Lucide | Keep-apart relationship rule; may wrap existing `IconBan` semantics. |
| `IconCatalog` | `Library` | Lucide | `Katalog` route/surface. |
| `IconVaultFiles` | `FolderOpen` | Lucide | `Mina filer` and vault surfaces. |
| `IconRun` | `Play` | Lucide | Execute/run/test-run actions. |
| `IconRunHistory` | `History` | Lucide | `Mina körningar` and run-history surfaces. |
| `IconDebug` | `Bug` | Lucide | Debug affordances. |
| `IconCode` | `Code` | Lucide | Code/editor surfaces. |
| `IconProfile` | `CircleUserRound` | Lucide | Profile/account surfaces. |
| `IconRole` | `ShieldUser` | Lucide | Role/permission surfaces. |
| `IconAi` | `Sparkles` | Lucide | AI feature semantics. |
| `IconSpinner` | `LoaderCircle` | Lucide | Shared dense/loading spinner wrapper. |
| `IconAdjustments` | `SlidersHorizontal` | Lucide | Replace current custom SVG internals while preserving wrapper name. |
| `IconFitView` | `Fullscreen` | Lucide | Replace current custom SVG internals while preserving fit-view semantics. |
| `IconMinus` | `Minus` | Lucide | Replace current custom SVG internals while preserving wrapper name. |
| `IconZoomIn` | `ZoomIn` | Lucide | Replace current custom SVG internals while preserving wrapper name. |
| `IconZoomOut` | `ZoomOut` | Lucide | Replace current custom SVG internals while preserving wrapper name. |

## Approved Fallback Icon Exceptions

Lucide proper remains the default runtime source. `PR-0293` may introduce Tabler
only for these named slots unless a later decision explicitly expands this
table:

| Semantic slot | Fallback source | Approved icon | Reason |
|---|---|---|---|
| Groups workspace | Tabler | `users-group` | Clearer teacher-facing group-workspace symbol than Lucide `Group` and avoids overloading `UsersRound`. |
| Classroom | Tabler | `chalkboard-teacher` | Best match for one classroom/classroom-template semantics; Lucide `School` is too broad. |

## Rules

- A symbol may represent one primary semantic concept. Do not use one icon for
  unrelated concepts such as actual share links and proximity rules.
- A behavior is not a semantic slot. For example, `menu`, `toggle`, and `split`
  are interaction behaviors; they should not force new domain symbols.
- Prefer Lucide-backed wrappers for canonical icons. Direct Lucide imports are
  allowed only inside icon wrappers or explicitly approved local leaf
  components.
- Hand-rolled SVGs need a written reason. If Lucide has a suitable canonical
  symbol, use the Lucide-backed wrapper instead.
- Destructive actions keep the existing burgundy/danger language and should not
  borrow symbols that imply ordinary editing.
- Final decisions must be captured in docs before runtime implementation.

## Locked Custom SVG Replacement Map

All currently hand-authored shared SVG wrappers have Lucide counterparts in the
installed `lucide-vue-next@0.563.0` package. `PR-0293` should replace the
wrapper internals with these Lucide-backed components while preserving the
existing wrapper names where that keeps runtime call sites stable.

| Current wrapper | Current semantic slot | Lucide replacement | Runtime instruction |
|---|---|---|---|
| `IconAdjustments` | Configure/context settings for dense tools | `SlidersHorizontal` | Keep `IconAdjustments` as the exported wrapper name unless `PR-0292` renames the semantic slot; replace the inline SVG with `SlidersHorizontal`. |
| `IconFitView` | Fit canvas/viewport to available space | `Fullscreen` | Keep `IconFitView` as the exported wrapper name so the control remains "fit view", not a fullscreen action; replace the inline SVG with `Fullscreen`. |
| `IconMinus` | Remove/decrement stepper action | `Minus` | Replace the inline SVG with `Minus`; keep the wrapper paired with `IconPlus`. |
| `IconZoomIn` | Zoom in | `ZoomIn` | Replace the inline SVG with `ZoomIn`. |
| `IconZoomOut` | Zoom out | `ZoomOut` | Replace the inline SVG with `ZoomOut`. |

No compatible EdTech add-on icon library is needed for these five custom SVGs.
Future add-on evaluation should only start when the complete local Lucide
inventory lacks a suitable semantic candidate.

## Deliverables

- A complete visual index under `docs/mockups/st-29-12-symbol-inventory/`.
- A semantic decision table covering approved, rejected, and deferred symbols.
- A code-facing mapping from semantic slots to wrapper/component names.
- Follow-up PR tasks that apply the mapping without changing layout contracts.
