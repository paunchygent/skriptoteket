---
type: reference
id: REF-SKRIPT-GENERAL-shared-tool-control-language-and-primitive-matrix-v1-PART-01
title: Shared tool control language and primitive matrix v1 — part 01
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-shared-tool-control-language-and-primitive-matrix-v1
part: 1
---

## Overview

### Source: Purpose

This note defines the first stable cross-app control language for tool-grade Skriptoteket surfaces.
Its first consumers are Klassrumskartan and the code editor.

The goal is not to catalog every possible control. The goal is to lock the minimal shared core that
already clearly exists across both tools so shared primitives can evolve once and then propagate
everywhere they are used.

This v1 also establishes an important modeling constraint:

- `semantic role` is not the same thing as `interaction behavior`
- `split`, `toggle`, and `menu` are not new role categories
- compact compound controls should be modeled as compositions of stable primitives rather than as
  one-off special buttons

In practice, the shared control language is defined in three layers:

1. `semantic role`
   Examples: `primary_cta`, `secondary_action`, `toolbar_action`, `destructive_action`,
   `overflow_action`
2. `interaction behavior`
   Examples: `direct`, `split`, `toggle`, `menu`
3. `composition rule`
   Example: a visible feature toggle paired with a related `configure_context` child action

This separation keeps the design system small and stable. We do not create a new role every time a
control gains a split affordance, an on/off state, or a related branch into deeper configuration.

### Source: Scope

- Repeated operational controls in dense desktop tools
- Shared semantic roles for those controls
- Shared interaction behaviors for those controls
- Shared composition rules for compact compound controls
- Shared primitive expectations for symbol, label visibility, and placement behavior

## Facts And Semantics

### Source: Foundational invariants

- One shared operation must not get different symbols, semantic roles, or base primitive treatments
  in different tools.
- Most dense-workspace controls are not CTAs. They are operational toolbar actions.
- Split behavior, toggle behavior, and menu behavior do not create new semantic categories on their
  own.
- If a control combines a feature state and a related tuning path, prefer a compact compound control
  built from stable primitives instead of inventing a special-case button family.
- App-specific composition may vary, but shared primitives must not drift by app.
- If an operation is ambiguous, app-specific, destructive, or high-commitment, visible text stays
  present even when an icon is used.
- Dense toolbar labels must describe teacher-facing operations, not internal product concepts or
  implementation structure. Abstract helper labels such as `Klassrumsstöd` must not ship as visible
  standalone toolbar copy.
- Dense toolbar labels also should not narrate the verb that clicking performs when the control is
  already visibly interactive. Name the concept or tool (`Historik`), then express on/off through
  state feedback and explain the behavior in tooltip/help copy.
- When a binary option depends on an adjacent selector or context picker, the first-choice pattern
  is one grouped logical unit: selector on the left, explicit on/off affordance on the right,
  with active state shown directly and explanation carried by tooltip/accessibility copy rather
  than by a new verbose toolbar label.
- Editor and planner must not keep alternate glyph paths for the same frozen operation. For
  example, undo/redo should converge on the canonical icon components rather than mixing icon
  components and unicode arrows.
- If a repeated operation is not in this first-pass matrix, do not invent a new primitive casually.
  Propose it explicitly in a later revision once the stable core is implemented.
- When one stable shell hosts multiple mutually exclusive work surfaces, the mode switch must keep
  continuity through `ADR-SKRIPT-0077` / `REF-SKRIPT-RESEARCH-frontend-transition-continuity-pattern-and-adoption-inventory-v1` instead of through a
  blank `out-in` swap.

### Source: Shared modeling framework

This reference describes tool surfaces through five shared axes:

1. `topology layer`
2. `pattern typology`
3. `content role`
4. `interaction behavior`
5. `primitive ownership`

Together, these axes let us describe a page without inventing ad hoc language for each app.

### Topology layer glossary

| Topology layer | Professional meaning | Typical examples |
|----------------|----------------------|------------------|
| `app_shell` | the persistent frame that carries workspace identity, route exit, and cross-mode navigation | title block, exit action, mode switcher |
| `workspace_header` | the mode-local header area that introduces the current surface and its immediate view controls | workspace title, local view switch, helper copy |
| `command_surface` | the primary horizontal command area for contextual actions | toolbar, command row, split actions |
| `local_feedback_surface` | a local status or feedback area attached to recent system responses | export notice, inline success strip |
| `resume_surface` | a prominent dashboard area for continuing unfinished or resumable work | resume cards |
| `management_surface` | a structured dashboard area for managing core entities before entering deeper workspaces | class and classroom panels |
| `summary_surface` | a compact contextual summary area that keeps supporting state visible without taking over the page | smart-rules summary, selection summary |
| `support_surface` | a secondary working region adjacent to the main surface | student pool, tool rail |
| `canvas_control_zone` | the local control group attached to the dominant board/map/canvas | zoom controls, fit controls, current scale |
| `primary_surface` | the dominant work area where the main task is performed | room canvas, planning map |
| `inspector_surface` | a supporting side surface for selection details, object editing, or state inspection | active-rules inspector |
| `dialog_shell` | a modal or contained editor frame with its own heading, close affordance, and commit/dismiss actions | classroom editor modal |
| `dialog_footer` | the commit/dismiss command area of a modal or contained editor | modal footer buttons |

### Content role vocabulary

| Content role | Meaning |
|--------------|---------|
| `navigation` | changes mode, view, or route |
| `action` | performs or configures a state-changing command |
| `information` | presents status, context, counts, empty states, or guidance |
| `working_object` | represents a domain object that can be selected, moved, or acted on |
| `work_surface` | the surface that contains direct manipulation or inspection work |

### Pattern typology glossary

| Pattern term | Professional definition | Typical examples |
|--------------|-------------------------|------------------|
| `identity block` | a shell-level content block that names the current workspace and context | class/workspace title area |
| `route exit button` | a persistent action that leaves the current app or route context | `Avsluta` |
| `mode switcher` | a tablist or segmented control for mutually exclusive workspace modes | `Översikt` / `Grupper` / `Sittplatser` / `Regler` |
| `status strip` | a compact inline status row that communicates global or mode-local state | `Ingen ändring` strip |
| `context selector` | a form control that sets the current working context | classroom combobox |
| `command toolbar` | a grouped row of contextual workspace commands | seating action row |
| `icon button` | a compact direct-action button for canonical repeated operations | undo, redo, zoom |
| `command button` | a text or icon-led button used for explicit state-changing commands | `Slumpa`, `Nytt sittschema` |
| `switch toggle` | a binary control that expresses an on/off state | `Smart`, `Historik` |
| `compound control` | a compact composition of related primitives presented as one operational cluster | `Smart` toggle + configure child |
| `split button` | a compound action with a default command plus an adjacent disclosure for variants | `Exportera` + format disclosure |
| `menu button` | a trigger that reveals secondary contextual actions in a menu | overflow / more actions |
| `resume card` | a dashboard card whose primary job is to continue or reopen an in-progress workspace | `Fortsätt grupper`, `Fortsätt sittschema` |
| `management panel` | a structured dashboard panel for selecting, previewing, and managing a core entity | class panel, classroom panel |
| `preview surface` | a compact read-only preview of an entity before entering a deeper editor or workspace | roster preview, classroom preview |
| `resource list` | a structured list of selectable tools, versions, entities, or saved states used for opening, switching, or reviewing work | recent tools, my tools, version history |
| `summary strip` | a compact contextual summary area with counts, helper text, or lightweight controls | smart-rules summary |
| `inline notification` | a local feedback surface attached to a recent action outcome | export-ready strip |
| `modal dialog` | a contained editor surface that interrupts the current page to complete a focused editing task | classroom editor |
| `confirmation dialog` | a focused modal dialog that asks for explicit confirmation before a consequential action proceeds | delete class/classroom confirmation |
| `form field` | a standard labeled input for editing a scalar or multiline text value | classroom name input, class roster textarea |
| `stepper control` | a numeric adjustment control using adjacent increment/decrement triggers | width/height steppers |
| `tool palette` | a grouped set of creation/manipulation tools used inside an editor | room-object tools |
| `instruction panel` | compact guidance attached to an editor or workspace | `Så här gör du` |
| `tool rail` | a vertical supporting surface for tool selection and tool-local context | rules tool rail |
| `canvas header` | a local header attached to the primary surface | `Sittschema` header, map header |
| `zoom control group` | a clustered set of scale/view commands attached to a surface | `−` / `%` / `+` / `Anpassa` |
| `canvas` | a spatial work surface for direct manipulation, placement, or map-based authoring | room scene, planning map |
| `editor surface` | a keyboard-first editable text, code, or structured-document surface used for direct authoring | source code editor, JSON schema editors |
| `diff viewer` | a comparison surface that renders before/after changes across one or more files or fields | version diff, AI edit-op diff |
| `inspector` | a secondary panel for object details, lists, and editing affordances | rules inspector |
| `assistant panel` | a supplemental conversational workspace surface for guidance, chat, and proposed edits or actions | `Kodassistenten` |
| `entity token` | a visible representation of a domain object inside a list or map | student token |
| `spatial marker` | a structural or environmental object that anchors orientation in a spatial surface | whiteboard, door, teacher desk, seat placeholder |
| `empty state` | explicit messaging shown when a list, inspector, or stateful surface has no content yet | `Inga smarta regler ännu.` |
| `preview card` | a compact summary card attached to an editor to show a high-level state snapshot | classroom preview count card |

### Primitive ownership vocabulary

| Ownership | Meaning |
|-----------|---------|
| `shared_primitive` | one reusable primitive should be the same across tools |
| `shared_composition` | a repeatable arrangement of shared primitives |
| `mode_local_instance` | mode-specific content that inhabits a shared pattern without redefining the primitive |

### Source: Minimal interaction-behavior set

This v1 uses only four behavior patterns:

| Behavior | Meaning | Typical use |
|----------|---------|-------------|
| `direct` | one trigger performs one action immediately | undo, redo, fit view |
| `split` | the main trigger performs the default action and a secondary trigger opens related choices | export/download with format choice |
| `toggle` | the control expresses an on/off state | smart enabled/disabled, spellcheck enabled/disabled |
| `menu` | the control opens a list of related secondary actions | overflow, open recent, load variants |

These behaviors should cover the current stable core. If a future control does not fit one of them,
that is a signal to review the matrix deliberately rather than improvising a fifth behavior.

### Menu and split keyboard contract

First-pass shared expectations:

- `Enter` or `Space` activates the focused direct trigger.
- Split disclosures and menu buttons support `ArrowDown` to open and move into the menu.
- Open menus support `ArrowUp`, `ArrowDown`, `Home`, and `End`.
- `Escape` closes the menu and returns focus to the originating trigger.
- Split buttons return focus to the correct primary or disclosure trigger after menu dismissal.

### Source: Matrix A: Minimal Canonical Control Categories

| Category | Use when | Base primitive family | Visible label rule | Do not use for |
|----------|----------|-----------------------|--------------------|----------------|
| `primary_cta` | one dominant forward action moves the teacher/user into the next meaningful step | text action button | always text-visible; icon may support but never replace the label | routine canvas controls, undo/redo, local toggles |
| `secondary_action` | an important contextual action is needed, but it should not dominate the surface | text action button or icon-led text button | text visible by default on desktop toolbars and panels | the dominant next-step action, repeated micro-controls |
| `toolbar_action` | a repeated operational control acts on the current workspace, canvas, board, or inspector | compact icon button or compact icon-led button | icon-only allowed only when canonical, with tooltip and accessible name required | destructive actions, ambiguous app-specific actions, major flow commits |
| `destructive_action` | an action removes, clears, discards, or permanently reverses meaningful user work | explicit destructive text button or icon-led destructive button | text remains visible by default; icon can support but not replace | benign close/dismiss, routine toolbar actions |
| `overflow_action` | secondary actions exist but do not deserve permanent row presence | canonical overflow trigger | icon-only allowed with tooltip and accessible name | primary CTA, sole destructive path, critical contextual action |

### Source: Matrix B: First-Pass Shared Operation Inventory

| Operation | Canonical meaning | Used in now | Category | Behavior | Base primitive | Canonical symbol contract | Visible label rule |
|-----------|-------------------|-------------|----------|----------|----------------|---------------------------|--------------------|
| `undo` | revert the latest eligible user change | Klassrumskartan, Editor | `toolbar_action` | `direct` | compact icon button | undo arrow | icon-only allowed; tooltip + accessible name required |
| `redo` | restore the latest eligible reverted change | Klassrumskartan, Editor | `toolbar_action` | `direct` | compact icon button | redo arrow | icon-only allowed; tooltip + accessible name required |
| `history` | open past states, revisions, or recoverable prior work | Klassrumskartan, Editor | `toolbar_action` | `direct` | compact icon button or icon-led button | history/clock symbol | icon-only allowed in dense toolbars; text may appear in panels or drawers |
| `configure_context` | open the local configuration surface for the current workspace or tool | Klassrumskartan, Editor | `toolbar_action` | `direct` | compact icon button or icon-led button | adjustments/sliders symbol | icon-led or text-visible when the destination label needs disambiguation such as `Regler` or `Inställningar` |
| `create_new_entity` | create a new top-level draft, file, workspace object, or planning artifact | Klassrumskartan, Editor | `primary_cta` | `direct` | text action button | plus/add support symbol | text always visible; icon may support but does not replace the label |
| `dismiss_local_surface` | close a local drawer, modal, inspector, tab, or temporary panel | Klassrumskartan, Editor | `toolbar_action` | `direct` | compact icon button | close/x symbol | icon-only allowed for local dismiss; full workspace exit remains text-visible outside this first pass |
| `export_download` | export or download a user-facing artifact from the current tool | Klassrumskartan, Editor | `secondary_action` | `split` | text action button or icon-led text button | tray/download-export symbol | text visible by default; icon may support but does not replace the label |
| `zoom_in` | increase the canvas or document zoom level | Klassrumskartan, Editor | `toolbar_action` | `direct` | compact icon button | plus zoom symbol | icon-only allowed when grouped with other zoom controls and current scale is visible nearby |
| `zoom_out` | decrease the canvas or document zoom level | Klassrumskartan, Editor | `toolbar_action` | `direct` | compact icon button | minus zoom symbol | icon-only allowed when grouped with other zoom controls and current scale is visible nearby |
| `fit_view` | frame the active canvas or document into the intended working viewport | Klassrumskartan, Editor | `toolbar_action` | `direct` | compact icon button or icon-led button | fit/frame symbol | icon-only allowed when grouped with zoom controls and supported by tooltip + accessible name |
| `overflow_more` | reveal deferred secondary actions for the current local surface | Klassrumskartan, Editor | `overflow_action` | `menu` | overflow trigger | kebab/overflow symbol | icon-only by default; tooltip + accessible name required |

### Source: Primitive implementation guardrails for PR-0157

- Do not let parent surfaces such as `PlannerWorkspaceActionBar` own primitive sizing through
  descendant CSS overrides.
- Do not ship `configure_context` as icon-only when the teacher needs the destination label for
  confidence.
- Do not let split-button APIs hardcode planner-specific unions or default labels.
- Do not keep mixed symbol paths for frozen operations across planner and editor.
- Do not let segmented mode switches ship with ambiguous toggle-group semantics.

### Source: Worked topology: Klassrumskartan main mode and supporting mode

The live local planner at `http://127.0.0.1:5173/apps/classroom.group-seating-studio` shows the
relationship this reference is trying to formalize:

- `Sittplatser` is the main production mode
- `Regler` is the supporting tuning mode

The important design consequence is that the main mode should host compact operational controls,
while the supporting mode hosts the deeper authoring/tuning surface. We should not collapse the
supporting mode into an oversized toolbar drawer just because its entry point is compact.

### Seating workspace (`Sittplatser`) as main mode

| UI item | Pattern typology | Topology layer | Content role | Behavior | Ownership | Design implication |
|---------|------------------|----------------|--------------|----------|-----------|--------------------|
| workspace identity block | `identity block` | `app_shell` | `information` | — | `shared_composition` | anchors mode identity and current context |
| `Avsluta` | `route exit button` | `app_shell` | `navigation` | `direct` | `shared_primitive` | persistent route exit, not hidden in overflow |
| workspace switch (`Översikt` / `Grupper` / `Sittplatser` / `Regler`) | `mode switcher` | `app_shell` | `navigation` | `direct` | `shared_composition` | fixed-location mutually exclusive mode switch |
| `Ingen ändring` + helper line | `status strip` | `workspace_header` | `information` | — | `shared_composition` | thin global state signal, never a dominant banner |
| `Klassrum` selector | `context selector` | `command_surface` | `action` | `direct` | `shared_primitive` | context-setting form control, not CTA |
| `Ångra` | `icon button` | `command_surface` | `action / toolbar_action` | `direct` | `shared_primitive` | canonical cross-app undo control |
| `Gör om` | `icon button` | `command_surface` | `action / toolbar_action` | `direct` | `shared_primitive` | canonical cross-app redo control |
| `Slumpa` | `command button` | `command_surface` | `action / toolbar_action` | `direct` | `shared_primitive` | explicit workspace operation with visible label |
| `Smart` | `switch toggle` | `command_surface` | `action` | `toggle` | `shared_primitive` | collapsed feature-state control in the main mode |
| `Öppna Regler` | `icon button` inside a `compound control` | `command_surface` | `action / toolbar_action` | `direct` | `shared_composition` | configure child that routes to the supporting mode |
| `Börja om` | `command button` | `command_surface` | `action / destructive_action` | `direct` | `shared_primitive` | explicit reset/discard action with visible label |
| `Nytt sittschema` | `command button` | `command_surface` | `action / primary_cta` | `direct` | `shared_primitive` | top-level create action |
| `Exportera` | `split button` primary trigger | `command_surface` | `action / secondary_action` | `split` | `shared_primitive` | default export action |
| `Fler exportval` | `split button` disclosure trigger | `command_surface` | `action / secondary_action` | `split` | `shared_primitive` | branches into export variants without replacing the default action |
| `Fler sittplatsåtgärder` | `menu button` | `command_surface` | `action / overflow_action` | `menu` | `shared_primitive` | deferred secondary actions belong here |
| export status notice | `inline notification` | `local_feedback_surface` | `information` | — | `shared_composition` | local feedback should stay attached to the export lane |
| `Ladda ned igen` | `command button` | `local_feedback_surface` | `action / secondary_action` | `direct` | `shared_primitive` | immediate follow-up action inside local feedback |
| `Stäng exportstatus` | `icon button` | `local_feedback_surface` | `action / toolbar_action` | `direct` | `shared_primitive` | dismisses the feedback surface locally |
| smart-rules summary header/count | `summary strip` | `summary_surface` | `information` | — | `shared_composition` | compact supporting context in the main mode |
| `Historik` | `switch toggle` | `summary_surface` | `action` | `toggle` | `shared_primitive` | lightweight concept toggle kept near the feature summary; behavior is explained in tooltip/help |
| smart-rules helper text / empty state | `summary strip` + `empty state` | `summary_surface` | `information` | — | `mode_local_instance` | points to `Regler` instead of expanding inline complexity |
| student pool panel | `support_surface` containing `entity tokens` | `support_surface` | `work_surface` | — | `shared_composition` | secondary working region beside the main canvas |
| student count badge | count/status affordance inside support panel | `support_surface` | `information` | — | `shared_primitive` | compact quantitative context |
| student token in pool | `entity token` | `support_surface` | `working_object` | `direct` | `shared_primitive` | movable/selectable domain object |
| `Sittschema` header + helper copy | `canvas header` | `workspace_header` | `information` | — | `shared_composition` | introduces the primary surface without excessive prose |
| zoom percentage readout | part of `zoom control group` | `canvas_control_zone` | `information` | — | `shared_composition` | local scale feedback |
| `−` | `icon button` in `zoom control group` | `canvas_control_zone` | `action / toolbar_action` | `direct` | `shared_primitive` | canonical zoom-out control |
| `+` | `icon button` in `zoom control group` | `canvas_control_zone` | `action / toolbar_action` | `direct` | `shared_primitive` | canonical zoom-in control |
| `Anpassa` | `command button` in `zoom control group` | `canvas_control_zone` | `action / toolbar_action` | `direct` | `shared_primitive` | canonical fit-view control |
| room canvas | `canvas` | `primary_surface` | `work_surface` | — | `shared_composition` | dominant production surface |
| seat targets / seat placeholders | `spatial marker` | `primary_surface` | `working_object` | — | `mode_local_instance` | defines potential placement targets inside the canvas |
| room fixtures (`Kateder`, desks, `Whiteboard`, `Dörr`) | `spatial marker` | `primary_surface` | `information` | — | `mode_local_instance` | environmental orientation anchors |

### Rules workspace (`Regler`) as supporting mode

| UI item | Pattern typology | Topology layer | Content role | Behavior | Ownership | Design implication |
|---------|------------------|----------------|--------------|----------|-----------|--------------------|
| workspace identity block | `identity block` | `app_shell` | `information` | — | `shared_composition` | same shell identity pattern as the main mode |
| `Avsluta` | `route exit button` | `app_shell` | `navigation` | `direct` | `shared_primitive` | persistent route exit |
| workspace switch (`Översikt` / `Grupper` / `Sittplatser` / `Regler`) | `mode switcher` | `app_shell` | `navigation` | `direct` | `shared_composition` | fixed-location workspace navigation |
| `Ingen ändring` + helper line | `status strip` | `workspace_header` | `information` | — | `shared_composition` | stable shell status in the supporting mode too |
| tool-rail header (`Verktyg`) | `tool rail` header | `support_surface` | `information` | — | `shared_composition` | introduces the tool palette |
| tool selection button (`Närmare läraren`, `Håll isär`, `Håll nära`) | `command button` in a `tool rail` | `support_surface` | `action` | `direct` | `shared_composition` | domain-specific tools keep visible labels |
| selection summary (`Markering`, `0 valda`) | `summary strip` | `support_surface` | `information` | — | `shared_composition` | local selection state belongs near the tool rail |
| `Rensa markering` | `command button` | `support_surface` | `action / destructive_action` | `direct` | `shared_primitive` | local reset action for the current selection |
| map header (`Kartvy` + helper copy) | `canvas header` | `workspace_header` | `information` | — | `shared_composition` | explains the current authoring view |
| `Planeringskarta` / `Sittschema` switch | `mode switcher` / segmented view control | `workspace_header` | `navigation` | `direct` | `shared_composition` | local mutually exclusive map view switch |
| map-availability helper text | `status strip` | `workspace_header` | `information` | — | `mode_local_instance` | compact capability messaging, not a new panel |
| zoom percentage readout | part of `zoom control group` | `canvas_control_zone` | `information` | — | `shared_composition` | local scale feedback |
| `−` | `icon button` in `zoom control group` | `canvas_control_zone` | `action / toolbar_action` | `direct` | `shared_primitive` | canonical zoom-out control |
| `+` | `icon button` in `zoom control group` | `canvas_control_zone` | `action / toolbar_action` | `direct` | `shared_primitive` | canonical zoom-in control |
| `Anpassa` | `command button` in `zoom control group` | `canvas_control_zone` | `action / toolbar_action` | `direct` | `shared_primitive` | canonical fit-view control |
| planning map | `canvas` | `primary_surface` | `work_surface` | — | `shared_composition` | dominant supporting authoring surface |
| student node on map | `entity token` | `primary_surface` | `working_object` | `direct` | `shared_primitive` | selectable map object for rule authoring |
| seat placeholders and room fixtures | `spatial marker` | `primary_surface` | `information` | — | `mode_local_instance` | environmental/spatial structure of the map |
| inspector header (`Inspektör`) | `inspector` header | `inspector_surface` | `information` | — | `shared_composition` | declares the supporting editing surface |
| `Aktiva regler` count | inspector metadata block | `inspector_surface` | `information` | — | `shared_composition` | compact state summary for authored rules |
| rule list or empty state | `inspector` body + `empty state` | `inspector_surface` | `information` / `work_surface` | — | `shared_composition` | the inspector supports the map rather than competing with it |

### Source: Worked topology: Overview as coordination mode

`Översikt` is not a canvas mode. It is a coordination/dashboard mode that decides what the teacher
continues, changes, or enters next. Its language therefore leans more on dashboard patterns than on
canvas patterns, but it still uses the same shell, action, and management vocabulary.

### Overview workspace (`Översikt`) as coordination mode

| UI item | Pattern typology | Topology layer | Content role | Behavior | Ownership | Design implication |
|---------|------------------|----------------|--------------|----------|-----------|--------------------|
| workspace identity block | `identity block` | `app_shell` | `information` | — | `shared_composition` | same shell identity pattern as other modes |
| `Avsluta` | `route exit button` | `app_shell` | `navigation` | `direct` | `shared_primitive` | persistent route exit |
| workspace switch (`Översikt` / `Grupper` / `Sittplatser` / `Regler`) | `mode switcher` | `app_shell` | `navigation` | `direct` | `shared_composition` | fixed-location workspace navigation |
| overview mode label | shell-level workspace label | `workspace_header` | `information` | — | `mode_local_instance` | lightweight mode confirmation, not a second major header |
| `Fortsätt grupper` container | `resume card` | `resume_surface` | `information` | — | `shared_composition` | resumable-work shell, not a generic management card |
| `Stäng fortsätt grupper` | `icon button` | `resume_surface` | `action / toolbar_action` | `direct` | `shared_primitive` | local dismiss of a resumable card |
| `Fortsätt grupper` action | `command button` | `resume_surface` | `action / primary_cta` | `direct` | `shared_primitive` | enter the resumable workspace directly |
| `Fortsätt sittschema` container | `resume card` | `resume_surface` | `information` | — | `shared_composition` | resumable-work shell for seating |
| `Stäng fortsätt sittschema` | `icon button` | `resume_surface` | `action / toolbar_action` | `direct` | `shared_primitive` | local dismiss of a resumable card |
| `Fortsätt sittschema` action | `command button` | `resume_surface` | `action / primary_cta` | `direct` | `shared_primitive` | enter the resumable seating workspace directly |
| class panel shell | `management panel` | `management_surface` | `work_surface` | — | `shared_composition` | dashboard management surface for the class entity |
| `Byt klass` selector | `context selector` | `management_surface` | `action` | `direct` | `shared_primitive` | selects the active class entity |
| roster preview | `preview surface` | `management_surface` | `information` | — | `shared_composition` | compact read-only preview before deeper edits |
| `Ny klasslista` | `command button` | `management_surface` | `action / primary_cta` | `direct` | `shared_primitive` | create new class entity |
| `Redigera klass` | `command button` | `management_surface` | `action / secondary_action` | `direct` | `shared_primitive` | edit existing class entity |
| `Ta bort klasslista` | `command button` | `management_surface` | `action / destructive_action` | `direct` | `shared_primitive` | explicit destructive action |
| classroom panel shell | `management panel` | `management_surface` | `work_surface` | — | `shared_composition` | dashboard management surface for the classroom entity |
| `Välj klassrum` selector | `context selector` | `management_surface` | `action` | `direct` | `shared_primitive` | selects the active classroom entity |
| classroom preview | `preview surface` | `management_surface` | `information` | — | `shared_composition` | compact spatial preview before deeper edits |
| `Nytt klassrum` | `command button` | `management_surface` | `action / primary_cta` | `direct` | `shared_primitive` | create new classroom entity |
| `Redigera klassrum` | `command button` | `management_surface` | `action / secondary_action` | `direct` | `shared_primitive` | enters the classroom editor |
| `Ta bort klassrum` | `command button` | `management_surface` | `action / destructive_action` | `direct` | `shared_primitive` | explicit destructive action |

### Source: Worked topology: Classroom editor as contained editor mode

The classroom editor is neither a dashboard mode nor a planner canvas mode. It is a contained
editor mode presented as a modal dialog. That means it should use editor vocabulary:

- modal shell
- properties/support panel
- tool palette
- dominant editing canvas
- explicit modal footer actions

### Classroom editor (`Redigera klassrum`) as contained editor mode

| UI item | Pattern typology | Topology layer | Content role | Behavior | Ownership | Design implication |
|---------|------------------|----------------|--------------|----------|-----------|--------------------|
| editor modal shell | `modal dialog` | `dialog_shell` | `work_surface` | — | `shared_composition` | contained editor frame with its own editing lifecycle |
| modal title block (`Klassrum`, `Redigera klassrum`) | `identity block` | `dialog_shell` | `information` | — | `shared_composition` | establishes the contained editing context |
| modal close (`×`) | `icon button` | `dialog_shell` | `action / toolbar_action` | `direct` | `shared_primitive` | local dismiss for the editor |
| classroom name field | `form field` | `support_surface` | `action` | `direct` | `shared_primitive` | scalar property editor |
| width control | `stepper control` | `support_surface` | `action` | `direct` | `shared_primitive` | bounded numeric property adjustment |
| height control | `stepper control` | `support_surface` | `action` | `direct` | `shared_primitive` | bounded numeric property adjustment |
| tool palette shell (`Verktyg`) | `tool palette` | `support_surface` | `work_surface` | — | `shared_composition` | grouped editor tools for object placement/manipulation |
| tool button (`Placera plats`, `Whiteboard`, `Fönster`, `Dörr`, `Kateder`, tables, `Bänk`, `Sudda`, `Rensa`) | `command button` inside a `tool palette` | `support_surface` | `action` | `direct` | `shared_composition` | tool selection / editing commands with explicit labels |
| help block (`Så här gör du`) | `instruction panel` | `support_surface` | `information` | — | `shared_composition` | editor-local guidance, kept compact |
| canvas header (`Klassrumsyta`) | `canvas header` | `workspace_header` | `information` | — | `shared_composition` | introduces the editor canvas without competing with it |
| zoom percentage readout | part of `zoom control group` | `canvas_control_zone` | `information` | — | `shared_composition` | local scale feedback |
| `−` | `icon button` in `zoom control group` | `canvas_control_zone` | `action / toolbar_action` | `direct` | `shared_primitive` | canonical zoom-out control |
| `+` | `icon button` in `zoom control group` | `canvas_control_zone` | `action / toolbar_action` | `direct` | `shared_primitive` | canonical zoom-in control |
| `Anpassa` | `command button` in `zoom control group` | `canvas_control_zone` | `action / toolbar_action` | `direct` | `shared_primitive` | canonical fit-view control |
| editor canvas | `canvas` | `primary_surface` | `work_surface` | — | `shared_composition` | dominant editing surface |
| placement grid / hit targets | editor-local grid affordance | `primary_surface` | `working_object` | — | `mode_local_instance` | interaction scaffold for object placement |
| placed seats and fixtures | `spatial marker` | `primary_surface` | `working_object` / `information` | `direct` | `mode_local_instance` | editor-local object instances inside the canvas |
| preview count card (`Förhandsvisning`) | `preview card` | `support_surface` | `information` | `direct` | `shared_composition` | compact readout of editor result/state |
| `Radera klassrum` | `command button` | `dialog_footer` | `action / destructive_action` | `direct` | `shared_primitive` | explicit destructive footer action |
| `Avbryt` | `command button` | `dialog_footer` | `navigation` | `direct` | `shared_primitive` | dismiss editor without commit |
| `Spara klassrum` | `command button` | `dialog_footer` | `action / primary_cta` | `direct` | `shared_primitive` | explicit commit action for the contained editor |

### Source: Worked topology: Classlist editor as structured form mode

The classlist editor does not introduce a second editor family. It is still a `modal dialog`, but
its dominant surface is a structured form rather than a spatial canvas. Create and edit states are
state variants of the same editor pattern, not new typologies.

### Classlist editor (`Ny klasslista` / `Redigera klasslista`) as structured form mode
