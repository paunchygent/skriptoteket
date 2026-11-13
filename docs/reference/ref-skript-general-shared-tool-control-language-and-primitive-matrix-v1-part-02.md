---
type: reference
id: REF-SKRIPT-GENERAL-shared-tool-control-language-and-primitive-matrix-v1-PART-02
title: Shared tool control language and primitive matrix v1 — part 02
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-shared-tool-control-language-and-primitive-matrix-v1
part: 2
---

| UI item | Pattern typology | Topology layer | Content role | Behavior | Ownership | Design implication |
|---------|------------------|----------------|--------------|----------|-----------|--------------------|
| classlist editor modal shell | `modal dialog` | `dialog_shell` | `work_surface` | — | `shared_composition` | contained editor frame with create/edit lifecycle |
| modal title block (`Klasslistor`, `Ny klasslista` / `Redigera klasslista`) | `identity block` | `dialog_shell` | `information` | — | `shared_composition` | editor identity changes by state, not by pattern type |
| modal close (`×`) | `icon button` | `dialog_shell` | `action / toolbar_action` | `direct` | `shared_primitive` | local dismiss for the editor |
| import block shell | `instruction panel` | `support_surface` | `information` | — | `shared_composition` | compact ingress block for file-based population |
| supported file-format copy | `instruction panel` | `support_surface` | `information` | — | `mode_local_instance` | explains acceptable import sources without becoming a separate workflow surface |
| `Importera från fil` | `command button` | `support_surface` | `action / secondary_action` | `direct` | `shared_primitive` | file-ingress action attached to the editor, not a new modal family |
| class name field | `form field` | `support_surface` | `action` | `direct` | `shared_primitive` | single-value identity field |
| student-list field (`Elever`) | `form field` | `support_surface` | `action` | `direct` | `shared_primitive` | multiline bulk-input field for roster authoring; stays inside the form-field family |
| student count metadata | inline metadata attached to the roster field | `support_surface` | `information` | — | `shared_composition` | lightweight progress/count signal for the current list |
| roster helper copy | helper text attached to the roster field | `support_surface` | `information` | — | `shared_composition` | keeps input grammar explicit without adding a new panel |
| `Radera klasslista` | `command button` | `dialog_footer` | `action / destructive_action` | `direct` | `shared_primitive` | destructive footer action in edit state only |
| `Avbryt` | `command button` | `dialog_footer` | `navigation` | `direct` | `shared_primitive` | dismiss editor without commit |
| `Skapa klasslista` / `Spara ändringar` | `command button` | `dialog_footer` | `action / primary_cta` | `direct` | `shared_primitive` | primary commit action varies by create/edit state, not by primitive family |

### Source: Worked topology: Code editor hub as coordination mode

The code editor hub at `/editor?pick=1` is a coordination surface for authoring work. Like
`Översikt`, it does not do the primary work itself. It helps the contributor resume, search, pick,
or create the next tool to edit.

### Code editor hub (`Kodredigeraren`) as coordination mode

| UI item | Pattern typology | Topology layer | Content role | Behavior | Ownership | Design implication |
|---------|------------------|----------------|--------------|----------|-----------|--------------------|
| workspace identity block | `identity block` | `app_shell` | `information` | — | `shared_composition` | establishes the authoring context and purpose of the hub |
| supporting links (`Mina verktyg`, `Alla verktyg`) | navigation links inside the header | `workspace_header` | `navigation` | `direct` | `mode_local_instance` | secondary wayfinding stays lightweight and subordinate to the hub task |
| hub search field | `form field` | `workspace_header` | `action` | `direct` | `shared_primitive` | canonical search affordance for opening a tool without changing the surrounding shell |
| search results overlay | `resource list` | `support_surface` | `work_surface` | `direct` | `shared_composition` | transient result surface attached to the search field, not a separate page |
| `Skapa nytt verktyg` | `command button` | `workspace_header` | `action / primary_cta` | `direct` | `shared_primitive` | create path remains a simple top-level CTA and reuses the standard modal editor entry |
| recents panel shell (`Senast öppnade`) | `management panel` | `resume_surface` | `work_surface` | — | `shared_composition` | resumable authoring work belongs in a dedicated, calm panel |
| recent-tools list | `resource list` | `resume_surface` | `work_surface` | `direct` | `shared_composition` | recent items are selectable work entries, not cards with bespoke chrome |
| `Inga senaste verktyg än.` | `empty state` | `resume_surface` | `information` | — | `shared_composition` | empty recents should stay explicit and lightweight |
| my-tools panel shell (`Mina verktyg`) | `management panel` | `management_surface` | `work_surface` | — | `shared_composition` | stable entity-management panel for owned tools |
| my-tools list | `resource list` | `management_surface` | `work_surface` | `direct` | `shared_composition` | owned tools are selected from a list, not a second dashboard card family |

### Source: Worked topology: Tool editor as dense authoring mode

The tool editor at `/admin/tools/:toolId` is the strongest current test of the shared language. It
is not a form page and not a spatial canvas. It is a dense desktop authoring workspace with:

- a stable authoring shell
- a command row with save/open, tool switching, workflow actions, and mode switching
- one canonical primary authoring surface in `Källkod`
- supporting modes for comparison, metadata, and testing
- a persistent assistant support surface

The key consequence is that the editor should compose from stable types rather than inventing a
bespoke shell for each mode.

### Tool editor shell and source mode

| UI item | Pattern typology | Topology layer | Content role | Behavior | Ownership | Design implication |
|---------|------------------|----------------|--------------|----------|-----------|--------------------|
| editable tool identity block (`Titel`, `Sammanfattning`, `URL-namn`) | `identity block` + `summary strip` | `app_shell` | `information` / `action` | `direct` | `shared_composition` | the editor shell owns tool identity, but the identity area stays compact and inline-editable |
| `Spara/Öppna` | `menu button` | `command_surface` | `action / secondary_action` | `menu` | `shared_primitive` | save, checkpoint, and open-history actions are grouped behind one stable command trigger |
| `Verktyg` | `menu button` | `command_surface` | `action / overflow_action` | `menu` | `shared_primitive` | tool switching and tool creation branch from one shared resource-switch command |
| publication state line (`Ej publicerad · Ny arbetsversion`) | `status strip` | `workspace_header` | `information` | — | `shared_composition` | publication state belongs in the shell, not as a large alert band |
| workflow action cluster (`Begär publicering`, `Publicera`, `Avslå`) | `command toolbar` | `command_surface` | `action` | `direct` | `shared_composition` | role-dependent workflow actions stay grouped and explicit |
| editor-mode switch (`Källkod`, `Diff`, `Metadata`, `Testkör`) | `mode switcher` | `workspace_header` | `navigation` | `direct` | `shared_composition` | mode changes are explicit, mutually exclusive, and remain inside one stable shell |
| source code surface | `editor surface` | `primary_surface` | `work_surface` | `direct` | `shared_composition` | canonical authoring surface for the editor; this is the editor equivalent of a primary canvas |
| schema support section header (`Indata & inställningar (JSON)`) | support section header | `support_surface` | `information` | — | `shared_composition` | secondary authoring surfaces stay subordinate to the primary code editor |
| `Visa` / `Dölj` schema section toggle | `command button` | `support_surface` | `action / toolbar_action` | `toggle` | `shared_primitive` | support surfaces can collapse without changing the main editing model |
| `Indata` JSON editor | `editor surface` | `support_surface` | `work_surface` | `direct` | `shared_composition` | structured text authoring still belongs to the editor-surface family |
| `Inställningar` JSON editor | `editor surface` | `support_surface` | `work_surface` | `direct` | `shared_composition` | settings authoring reuses the same primary primitive family as source editing |
| `formatera` | `command button` | `support_surface` | `action / toolbar_action` | `direct` | `shared_primitive` | routine formatting remains a compact support action |
| `förval` | `menu button` | `support_surface` | `action / toolbar_action` | `menu` | `shared_primitive` | schema presets branch from a compact menu instead of adding shell clutter |
| `Kodassistenten` | `assistant panel` | `support_surface` | `work_surface` | — | `shared_composition` | conversational support is a persistent secondary workspace, not a modal interruption |
| assistant composer | `form field` | `support_surface` | `action` | `direct` | `shared_primitive` | prompt composition stays inside the assistant panel rather than the global shell |
| assistant mode tabs (`Chat`, `Edit`) | `mode switcher` | `support_surface` | `navigation` | `direct` | `shared_composition` | assistant-local modes follow the same segmented-switch rule as workspace modes |
| `Minimera kodassistenten` / `Expandera kodassistenten` | `icon button` | `support_surface` | `action / toolbar_action` | `direct` | `shared_primitive` | support surfaces may collapse, but the collapsed rail remains part of the same panel family |

### Diff mode as comparison surface

| UI item | Pattern typology | Topology layer | Content role | Behavior | Ownership | Design implication |
|---------|------------------|----------------|--------------|----------|-----------|--------------------|
| compare target selector (`Diff mot`) | `context selector` | `command_surface` | `action` | `direct` | `shared_primitive` | comparison target selection is a context-setting action, not a bespoke diff control family |
| `Stäng diff` | `command button` | `command_surface` | `navigation` | `direct` | `shared_primitive` | exits comparison mode explicitly without changing the shell |
| diff surface | `diff viewer` | `primary_surface` | `work_surface` | — | `shared_composition` | before/after comparison is a distinct reusable surface type, not a variant of spatial canvas or plain text editor |
| `Ingen diff att visa.` | `empty state` | `primary_surface` | `information` | — | `shared_composition` | the comparison mode fails gracefully without inventing a new error shell |

### Metadata mode and supporting dialog surfaces

| UI item | Pattern typology | Topology layer | Content role | Behavior | Ownership | Design implication |
|---------|------------------|----------------|--------------|----------|-----------|--------------------|
| `Verktygsinfo` panel | `management panel` | `management_surface` | `work_surface` | — | `shared_composition` | metadata editing is a structured management task, not a special editor family |
| title / slug / summary fields | `form field` | `management_surface` | `action` | `direct` | `shared_primitive` | scalar metadata continues to use the standard field family |
| profession/category selectors | `form field` groups | `management_surface` | `action` | `direct` | `shared_composition` | taxonomy selection remains part of the form system instead of spawning a dedicated picker type |
| `Instruktioner` panel | `instruction panel` | `management_surface` | `work_surface` | — | `shared_composition` | usage guidance is edited in its own supportive panel, not mixed into source mode |
| instructions markdown field | `form field` | `management_surface` | `action` | `direct` | `shared_primitive` | prose authoring stays inside the standard field family here |
| `Behörigheter` panel | `management panel` | `management_surface` | `work_surface` | — | `shared_composition` | collaborator management is another management surface, not a bespoke admin page |
| maintainer list | `resource list` | `management_surface` | `work_surface` | `direct` | `shared_composition` | maintainers are managed as list items inside the panel |
| add-maintainer field + action | `form field` + `command button` | `management_surface` | `action` | `direct` | `shared_composition` | add/remove flows compose from existing primitives |
| test-mode entrypoint selector | `context selector` | `command_surface` | `action` | `direct` | `shared_primitive` | test execution is configured via the standard selector family |
| `Spara ett utkast för att kunna testa.` | `empty state` | `primary_surface` | `information` | — | `shared_composition` | test mode uses a straightforward blocking empty state when execution prerequisites are missing |
| `Öppna sparade` popover | `modal dialog` | `dialog_shell` | `work_surface` | — | `shared_composition` | version/history access uses an existing dialog family rather than a bespoke history page |
| server-version list | `resource list` | `dialog_shell` | `work_surface` | `direct` | `shared_composition` | saved versions are selected from the same list family used elsewhere in the editor |
| checkpoint list | `resource list` | `dialog_shell` | `work_surface` | `direct` | `shared_composition` | local checkpoints remain part of the same saved-state selection model |

### Source: Code editor review outcome

The code editor review added a small but real set of reusable types:

- `resource list`
- `editor surface`
- `diff viewer`
- `assistant panel`

Everything else in the editor fit by composition:

- the create-tool flow is still a standard `modal dialog`
- the history/open-saved surface is still a dialog plus `resource list`
- metadata mode reuses `management panel`, `instruction panel`, `form field`, and `resource list`
- test mode currently fits existing selector + empty-state language
- save/open and tool switching remain `menu button` behaviors rather than new role categories

### Source: Notes on v1 restraint

- One genuinely reusable pattern emerged during the Klassrumskartan editor-facing review:
  `confirmation dialog`.
- The code-editor review added only the editor-specific archetypes that the existing language could not
  accurately name: `resource list`, `editor surface`, `diff viewer`, and `assistant panel`.
- The classlist editor did **not** require a second editor family. It fits the existing `modal dialog`
  model with form-centric content instead of canvas-centric content.
- The file-import block in the classlist editor is intentionally treated as an `instruction panel`
  plus a standard action, not as a separate primitive family.
- `create_new_entity` is intentionally narrower than generic "add anything" behavior. Inline add-row,
  add-chip, or add-node actions can be split later if they prove materially different.
- `dismiss_local_surface` covers local close behavior only. Full planner exit or route exit remains a
  separate text-visible control choice.
- `fit_view` stays merged in the first pass. If future tools prove that `reset_view` is a distinct
  meaning, the operation can split in v2.
- `configure_context` deliberately unifies local settings/rules/configure behavior around one shared
  symbol family while still allowing the visible label to remain domain-specific.

### Source: Implication for shared primitives

The next primitive layer should be built from this matrix outward:

- shared semantic roles first
- shared symbol contracts second
- shared button/icon/overflow primitives third
- app-specific toolbar composition only after those three stay stable

Klassrumskartan is the forcing function, but the output belongs to the shared design system rather
than to one app.

## Decisions And Interpretation

### Source: V1 freeze

This is the shortest canonical summary of the abstraction set. Read this before the longer matrices
and worked topologies.

### Frozen control roles

- `primary_cta`
- `secondary_action`
- `toolbar_action`
- `destructive_action`
- `overflow_action`

### Frozen interaction behaviors

- `direct`
- `split`
- `toggle`
- `menu`

### Frozen composition rule

- `toggle + configure_context child`

### Frozen reusable surface/pattern types

- `management panel`
- `modal dialog`
- `confirmation dialog`
- `resource list`
- `editor surface`
- `diff viewer`
- `assistant panel`

### Freeze rule

- If a new tool surface fits these abstractions plus the shared glossary below, do not invent a new
  abstraction.
- Only add a new abstraction when the current set genuinely fails to describe a reusable pattern.

### Frozen primitive constraints

- `configure_context` must not ship as a bare ambiguous gear when the destination needs
  disambiguation such as `Regler` or `Inställningar`; the first-pass symbol is
  `adjustments/sliders`, and the control becomes icon-led or text-visible when needed.
- Dense-action primitives own their own height, padding, icon size, disclosure width, and spacing.
  Parent toolbars may place primitives, but they should not normalize them with descendant
  selectors.
- When dense or planner-facing controls still rely on shared button classes instead of dedicated
  dense primitives, those repeated visual recipes should live in one shared class source rather
  than as per-surface inline class strings. Shared tuning must happen once and then propagate.
- Dense-action primitives also own their corner language. The default dense-tool family uses one
  hard small-radius treatment (`4px`) rather than mixing perfectly square and softly rounded
  standalone buttons on the same surface.
- Grouped controls keep that same family: outer edges carry the slight radius, while internal seams
  stay square/divided so split buttons, steppers, and clustered history controls still read as one
  blocky instrument.
- Split and menu primitives freeze as generic shared APIs, not planner-shaped widgets. Their item
  model and busy/disabled/menu-label contract should be reusable across planner and editor.
- The canonical segmented control is a single-choice mode switch, not a loose collection of pressed
  buttons.
- Disabled states freeze at `40%` for icon-tier dense actions and `50%` for text-visible actions.
- The first three size tiers are:
  - `dense_icon = 36px`
  - `dense_text = 28px`
  - `compact_segment = 24px`
- `compact_segment` may be used for segmented/toggle internals, but not as a standalone primary
  action-button target.

### Source: First-pass boundary

This v1 intentionally does **not** define the full operational primitive system yet.

Deferred from the shared operation inventory until the stable core is shipped:

- mode switches and segmented workspace tabs
- run/execute actions
- save/publish actions
- selection-specific commands
- navigation/back patterns
- a separate `reset view` primitive if it proves meaningfully different from `fit view`

### Source: Compound-control rule

Some mature workspace controls combine a feature state with a related configuration path.

The canonical first-pass pattern is:

- `toggle + configure_context child`

Use it when:

- the feature has a meaningful on/off state in the main workspace
- deeper tuning exists, but it is too large or too consequential for toolbar expansion
- the deeper tuning already has, or deserves, its own panel, drawer, or workspace

Example:

- `Smart` uses a visible on/off toggle in the seating/grouping toolbar
- the adjacent configure child uses the canonical configuration symbol
- selecting the configure child routes the teacher into `Regler` instead of opening a cramped
  toolbar drawer

This is intentionally not modeled as a separate semantic role. It is a composition of a `toggle`
behavior and a `configure_context` child action.

### Source: Main-mode / supporting-mode rule

When a feature has:

- a compact operational state in the main workspace, and
- a larger authoring or tuning surface elsewhere,

then the main workspace should expose only the collapsed operational face of that feature.

For Klassrumskartan:

- `Smart` in `Sittplatser` is the collapsed operational face
- `Regler` is the expanded tuning/authoring face

That means the compact control in the main mode should:

- let the teacher see the feature state immediately
- allow a direct on/off action when that state is meaningful
- route to the supporting mode for deeper tuning

It should **not** try to become a mini `Regler` workspace inside the seating toolbar.

### Source: Worked topology: Destructive confirmation as decision mode

The delete flows for classlists and classrooms reveal one genuinely reusable type that was not
named in the earlier pass: the `confirmation dialog`.

This is distinct from a general `modal dialog` because it does not host authoring work. Its job is
to pause the flow, restate the consequence, and force an explicit binary decision.

### Confirmation dialog (`Ta bort klasslista` / `Ta bort klassrum`) as decision mode

| UI item | Pattern typology | Topology layer | Content role | Behavior | Ownership | Design implication |
|---------|------------------|----------------|--------------|----------|-----------|--------------------|
| confirmation shell | `confirmation dialog` | `dialog_shell` | `work_surface` | — | `shared_composition` | focused consequence-check surface for a high-commitment action |
| confirmation heading block (`Ta bort …`, `Är du säker?`) | `identity block` | `dialog_shell` | `information` | — | `shared_composition` | restates object type and decision frame clearly |
| consequence copy | confirmation-specific message block | `dialog_shell` | `information` | — | `mode_local_instance` | explains blast radius before the destructive path is taken |
| `Avbryt` | `command button` | `dialog_footer` | `navigation` | `direct` | `shared_primitive` | explicit safe escape path |
| `Ta bort klasslista` / `Ta bort klassrum` | `command button` | `dialog_footer` | `action / destructive_action` | `direct` | `shared_primitive` | explicit destructive confirmation; never hidden behind iconography or overflow |
