---
type: mockup
id: MOCK-pr-0383-document-converter-swedish-copy-v4
title: "PR-0383 Document Converter Swedish copy v4"
status: approved
owners: "agents"
created: 2026-06-25
updated: 2026-06-25
tags:
  - PR-0383
  - ST-37-04
  - document-converter
  - copy
  - frontend-handoff
summary: "Locked Swedish UI copy handoff for the PR-0383 Document Converter mockup."
---

# PR-0383 Document Converter Swedish Copy V4

## Implementation Lock

This copy sheet is locked for `PR-0384` implementation by product-owner
approval on 2026-06-25. Production UI must implement these visible strings and
a11y labels as written, including `Exportera som`, `Enskilda PDF-filer`, and
`Kombinerad PDF`. Any route-visible copy change, visible output-choice change,
or reintroduction of `Båda`/`both` requires reopening the copy approval package
before implementation.

## Copy Direction

Use short, instrumental Swedish UI copy. The interface should not explain how
conversion works; it should help the teacher add material, choose export shape,
preview, download, save, or remove. Layout, icons, and selected state carry
context where text would otherwise over-explain. This follows the outcome-first
rule: the app owns rendering, safe file handling, and low-level decisions; the
user chooses only input and desired export result.

## Product Owner Change

The original inventory included three output modes: `separate PDFs`,
`combined PDF`, and `both`. The visible UI now exposes two choices:

| Field | Segment 1 | Segment 2 |
|---|---|---|
| Exportera som | Enskilda PDF-filer | Kombinerad PDF |

`dc.output.both` must not render in the UI. If the backend/API still accepts
`both` until a later contract change, the value may remain internal but must
not be exposed as a user choice.

## Case Rule

Store strings in normal Swedish case, for example `Mall`, `Ta bort`, and
`Förhandsvisa`. If a component renders labels or button text in uppercase, do
that in CSS. The brand lockup may use `DOKUMENTKONVERTERARE`.

## Visible UI Copy

| Copy id | Current placeholder | Recommended Swedish copy | Frontend note |
|---|---|---|---|
| dc.brand.product | DOCUMENT CONVERTER | DOKUMENTKONVERTERARE | Under `SKRIPTOTEKET`. Keep `SKRIPTOTEKET` outside this key. |
| dc.mode.project | HTML/CSS project | HTML/CSS | Default selected workspace. The layout shows that this is the project mode. |
| dc.mode.batch | Batch conversion | Flera dokument | Secondary lane. Avoid `batch` in visible copy. |
| dc.project.add_file | Add file | Lägg till fil | Full action in selected-file/control surface. |
| dc.project.add_short | Add | Lägg till | Compact group button, preferably rendered as `+ Lägg till`. |
| dc.project.total_loaded | 14 files loaded | {count} filer | Count chip. Avoid `inlästa` or `tillagda` when layout already carries context. |
| dc.project.html_count | 6 HTML | {count} HTML | Compact mobile overview. |
| dc.project.css_count | 3 CSS | {count} CSS | Compact mobile overview. |
| dc.project.image_count | 5 images | {count} bilder | Compact mobile overview. |
| dc.project.files_ready | Files ready | Filer | Status is carried by adjacent `Klar` or checkmark. |
| dc.project.template_ready | Template ready | Mall | Status is carried by adjacent `Klar` or checkmark. |
| dc.project.output_ready | Output ready | PDF | Short readiness label. |
| dc.asset.html_group | HTML files (6/10) | HTML ({count}/{max}) | File rows make `files` redundant. |
| dc.asset.css_group | CSS support (3/10) | CSS ({count}/{max}) | Placement makes CSS read as a support resource. |
| dc.asset.image_group | Images (5/10) | Bilder ({count}/{max}) | Clear and short. |
| dc.field.template | Template | Mall | Keep as a true form label. |
| dc.template.default | Default document | Standard | The dropdown is already labeled `Mall`. |
| dc.template.handout | Clean handout | Elevblad | More teacher-facing than `handout`. |
| dc.template.report_packet | Report packet | Rapport | Use `Rapportunderlag` only if the template is a working basis rather than a finished report style. |
| dc.field.output_mode | Output mode | Exportera som | The user chooses the export shape, not the file format. |
| dc.output.separate | Separate PDFs | Enskilda PDF-filer | Two-choice control. Requires an icon showing several separate PDF results. |
| dc.output.combined | Combined PDF | Kombinerad PDF | Two-choice control. Requires an icon showing several documents becoming one PDF. |
| dc.output.both | Both | Not rendered | Remove as visible choice. No button, segment, or tooltip. |
| dc.field.paper_size | Paper size | Format | Shorter than `Pappersstorlek`; A3/A4/A5 makes the meaning clear. |
| dc.paper.a3 | A3 | A3 | Do not localize paper code. |
| dc.paper.a4 | A4 | A4 | Do not localize paper code. |
| dc.paper.a5 | A5 | A5 | Do not localize paper code. |
| dc.readiness.files_checked | Project files checked | Filer | Avoid validation wording such as `kontrollerade`. |
| dc.readiness.template_selected | Template selected | Mall | Avoid `vald`; the status column says `Klar`. |
| dc.readiness.output_selected | Output selected | PDF | Short readiness label. |
| dc.status.ready | Ready | Klar | Repeated status value. |
| dc.preview.temporary | Temporary preview | Tillfällig | Enough in the preview footer. Standalone fallback: `Tillfällig förhandsvisning`. |
| dc.preview.discard | Discard preview | Ta bort | Destructive preview action. Standalone fallback: `Ta bort förhandsvisning`. |
| dc.preview.render | Render preview | Förhandsvisa | Replaces `rendera`; names the user's goal. |
| dc.preview.refresh | Refresh | Uppdatera | Short regeneration command. |
| dc.preview.download | Download PDF | Ladda ned | PDF is implied in the preview footer. Standalone fallback: `Ladda ned PDF`. |
| dc.preview.save | Save to Mina filer | Spara i Mina filer | Preserve `Mina filer` exactly as the product term. |

## Output Control

Final visible control:

| Field | Segment 1 | Segment 2 |
|---|---|---|
| Exportera som | Enskilda PDF-filer | Kombinerad PDF |

`Båda` is removed because it creates an unnecessary third result choice and
forces the user to manage more artifacts than the task requires.

## Output Icons

| Copy id | Visible label | Recommended icon | Avoid |
|---|---|---|---|
| dc.output.separate | Enskilda PDF-filer | Three separate PDF/document sheets with clear spacing. | Single file icon, stack, copy icon. |
| dc.output.combined | Kombinerad PDF | Several small documents going into one larger PDF document. | Single file icon, overlapping stack without direction, plus icon. |
| dc.output.both | Not rendered | No icon. | No fallback icon; the choice must not be visible. |

## Output A11y

| Copy id | Visible label | Accessible name |
|---|---|---|
| dc.output.separate | Enskilda PDF-filer | Skapa en PDF per dokument |
| dc.output.combined | Kombinerad PDF | Skapa en kombinerad PDF |
| dc.output.both | Not rendered | No label; the control is not rendered. |

## Accessibility And Landmarks

A11y copy may be slightly more explicit than visible copy, but still must avoid
mockup, backend, and rendering vocabulary.

| Copy id | Current placeholder | Recommended Swedish label | Frontend note |
|---|---|---|---|
| dc.a11y.workbench | Document Converter static mockup | Dokumentkonverterare | Remove `static mockup` language in production. |
| dc.a11y.phone_summary | Phone workspace summary | Mobilöversikt | Landmark for summarized mobile view. |
| dc.a11y.mode_group | Mode | Läge | Group label. |
| dc.a11y.project_context | Phone project context | Projektöversikt | Mobile project context. |
| dc.a11y.project_selector | Project and mode selector | Projekt | Desktop rail landmark. |
| dc.a11y.outcome_controls | Outcome controls | Val för export | Control area for template, export shape, and format. |
| dc.a11y.output_mode_group | Output mode | Exportera som | Matches visible control label. |
| dc.a11y.paper_size_group | Paper size | Format | Matches visible control label. |
| dc.a11y.readiness | Conversion readiness | Status | Avoid `conversion readiness` in Swedish. |
| dc.a11y.preview | PDF preview | Förhandsvisning | Pane landmark. |
| dc.a11y.preview_toolbar | Preview toolbar | Verktyg för förhandsvisning | Toolbar label. |
| dc.a11y.first_page | First page | Första sidan | Icon-only control. |
| dc.a11y.previous_page | Previous page | Föregående sida | Icon-only control. |
| dc.a11y.next_page | Next page | Nästa sida | Icon-only control. |
| dc.a11y.last_page | Last page | Sista sidan | Icon-only control. |
| dc.a11y.zoom_out | Zoom out | Zooma ut | Icon-only control. |
| dc.a11y.zoom_in | Zoom in | Zooma in | Icon-only control. |
| dc.a11y.preview_pages | Preview pages | Sidor | Thumbnail/page-strip landmark. |
| dc.a11y.rendered_page | Rendered PDF page preview | PDF-sida | Avoid `rendered`; name the object. |

## Icon-Only Controls

| Control | Visible? | aria-label |
|---|---|---|
| First page | Icon only | Första sidan |
| Previous page | Icon only | Föregående sida |
| Next page | Icon only | Nästa sida |
| Last page | Icon only | Sista sidan |
| Zoom out | Icon only | Zooma ut |
| Zoom in | Icon only | Zooma in |

## Other Icon Recommendations

| Action | Recommended icon | Note |
|---|---|---|
| dc.project.add_file / dc.project.add_short | Plus plus file, or plus in button | Plus alone is enough when the button is already in file/group context. |
| dc.preview.discard | Trash | Keep restrained/destructive styling. |
| dc.preview.render | Document with eye or preview icon | Better than a play triangle because the action is not media playback. |
| dc.preview.refresh | Circular arrow | Matches `Uppdatera`. |
| dc.preview.download | Down arrow | Standard. |
| dc.preview.save | Folder, preferably with plus/save marker | Should read as destination `Mina filer`, not a general download. |

## Symbol Store Rule

Production implementation must use the canonical shared icon wrappers from
`frontend/apps/skriptoteket/src/components/icons` before adding any Lucide
symbol. Direct Lucide usage belongs inside a wrapper or an explicitly approved
local leaf component.

Existing canonical wrappers cover `IconFileText`, `IconCode`, `IconPlus`,
`IconTrash`, `IconDownload`, `IconVaultFiles`, `IconZoomIn`, and `IconZoomOut`.
The Document Converter implementation may add Lucide-backed wrappers only for
semantic slots the store currently lacks, such as image assets, PDF preview,
refresh, page navigation, separate PDF output, and combined PDF output. Do not
use hand-drawn SVG or CSS geometry for these controls.

## Strings Not To Change Or Translate

The inventory explicitly treats file names, PDF preview content, dynamic page
or zoom values, and paper codes as not app copy.

| Surface | Examples | Handling |
|---|---|---|
| File names | `index.html`, `styles.css`, `cover.png` | User/project data. Do not translate. |
| PDF content | Headings, table text, placeholder text in the document | Source material/previewed document. Must not drive app copy. |
| Page and zoom values | `1 / 24`, `100%` | Dynamic preview state. |
| Paper codes | `A3`, `A4`, `A5` | Keep unchanged. |

## Frontend Decisions To Implement

1. Render two output segments, not three: `Enskilda PDF-filer` and
   `Kombinerad PDF`.
2. Do not show `dc.output.both`.
3. Use `Exportera som` as the output control label.
4. Change output icons: `Enskilda PDF-filer` shows several separate PDFs;
   `Kombinerad PDF` shows several documents becoming one PDF.
5. Use the canonical symbol store first; add Lucide-backed wrappers only for
   missing semantic slots.
6. Keep visible copy short and put full precision in a11y labels instead of
   explanatory UI text.
7. Preserve `Mina filer` exactly in `Spara i Mina filer`.
8. Avoid implementation terms: no labels such as `rendera`, `artifact`,
   `preview id`, `TTL`, `producer`, `backend`, or `validerad` in the user
   surface.
