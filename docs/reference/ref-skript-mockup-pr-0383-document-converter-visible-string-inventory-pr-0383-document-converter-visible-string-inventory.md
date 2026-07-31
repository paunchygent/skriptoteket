---
type: reference
id: REF-SKRIPT-MOCKUP-pr-0383-document-converter-visible-string-inventory
title: PR-0383 Document Converter visible string inventory
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: mockup
summary: PR-0383 Document Converter visible string inventory
---

## Intent

### PR-0383 Document Converter Visible String Inventory

### Scope

This inventory captures strings from the approved HTML/CSS mockup for
`PR-0384` production Vue implementation. The locked Swedish copy is recorded in
`swedish-copy-v4.md`.

Sample PDF document content is not product UI copy. It represents teacher
source material inside the preview and should not drive the application copy
proposal.

### Visible App Strings

| Copy id | Surface | Current placeholder | Notes |
|---|---|---|---|
| dc.brand.product | Top brand lockup | DOCUMENT CONVERTER | Route/app name treatment; `SKRIPTOTEKET` brand is not in scope. |
| dc.mode.project | Mode selector | HTML/CSS project | Default selected mode. |
| dc.mode.batch | Mode selector | Batch conversion | Secondary lane. |
| dc.project.add_file | Project controls | Add file | Full-width phone and desktop selected-file action. |
| dc.project.add_short | Project rail controls | Add | Compact rail action for a specific asset group. |
| dc.project.total_loaded | Phone project summary | 14 files loaded | Count summary; final implementation should bind number. |
| dc.project.html_count | Phone project summary | 6 HTML | Count summary; final implementation should bind number. |
| dc.project.css_count | Phone project summary | 3 CSS | Count summary; final implementation should bind number. |
| dc.project.image_count | Phone project summary | 5 images | Count summary; final implementation should bind number. |
| dc.project.files_ready | Phone readiness strip | Files ready | Summary status. |
| dc.project.template_ready | Phone readiness strip | Template ready | Summary status. |
| dc.project.output_ready | Phone readiness strip | Output ready | Summary status. |
| dc.asset.html_group | Desktop project rail | HTML files (6/10) | Group heading with cap. |
| dc.asset.css_group | Desktop project rail | CSS support (3/10) | CSS files are support assets, not primary documents. |
| dc.asset.image_group | Desktop project rail | Images (5/10) | Filename-bound raster assets only. |
| dc.field.template | Outcome controls | Template | Keep as a true control label. |
| dc.template.default | Template select | Default document | Option label. |
| dc.template.handout | Template select | Clean handout | Option label. |
| dc.template.report_packet | Template select | Report packet | Option label. |
| dc.field.output_mode | Outcome controls | Output mode | Keep as a true control label. |
| dc.output.separate | Output mode | Separate PDFs | Backend-supported output mode. |
| dc.output.combined | Output mode | Combined PDF | Backend-supported output mode. |
| dc.output.both | Output mode | Both | Backend-supported value that must not render as a visible user choice in v4. |
| dc.field.paper_size | Outcome controls | Paper size | Keep as a true control label. |
| dc.paper.a3 | Paper size | A3 | Do not localize paper code. |
| dc.paper.a4 | Paper size | A4 | Do not localize paper code. |
| dc.paper.a5 | Paper size | A5 | Do not localize paper code. |
| dc.readiness.files_checked | Desktop readiness | Project files checked | Status row, not an action. |
| dc.readiness.template_selected | Desktop readiness | Template selected | Status row, not an action. |
| dc.readiness.output_selected | Desktop readiness | Output selected | Status row, not an action. |
| dc.status.ready | Desktop readiness | Ready | Repeated status value. |
| dc.preview.temporary | Preview footer | Temporary preview | Communicate temporary state without TTL internals. |
| dc.preview.discard | Preview action | Discard preview | Destructive action. |
| dc.preview.render | Preview action | Render preview | Primary operational command but not navy-filled. |
| dc.preview.refresh | Preview action | Refresh | Regenerate current preview. |
| dc.preview.download | Preview action | Download PDF | Current artifact download. |
| dc.preview.save | Preview action | Save to Mina filer | Preserve `Mina filer` product term unless a naming question is raised. |

### Accessibility And Icon Labels

These labels may not all be visible text, but production implementation needs
clear accessible names for icon-only or symbolic controls.

| Copy id | Surface | Current placeholder | Notes |
|---|---|---|---|
| dc.a11y.workbench | Page landmark | Document Converter static mockup | Production should remove `static mockup` language. |
| dc.a11y.phone_summary | Phone section | Phone workspace summary | Accessibility-only landmark. |
| dc.a11y.mode_group | Mode control group | Mode | Accessibility-only label. |
| dc.a11y.project_context | Phone project card | Phone project context | Accessibility-only landmark. |
| dc.a11y.project_selector | Desktop rail | Project and mode selector | Accessibility-only landmark. |
| dc.a11y.outcome_controls | Center controls | Outcome controls | Accessibility-only landmark. |
| dc.a11y.output_mode_group | Output mode segments | Output mode | Accessibility-only group label. |
| dc.a11y.paper_size_group | Paper size segments | Paper size | Accessibility-only group label. |
| dc.a11y.readiness | Readiness panel | Conversion readiness | Accessibility-only landmark. |
| dc.a11y.preview | Preview pane | PDF preview | Accessibility-only landmark. |
| dc.a11y.preview_toolbar | Preview toolbar | Preview toolbar | Accessibility-only toolbar label. |
| dc.a11y.first_page | Preview toolbar | First page | Icon-only control. |
| dc.a11y.previous_page | Preview toolbar | Previous page | Icon-only control. |
| dc.a11y.next_page | Preview toolbar | Next page | Icon-only control. |
| dc.a11y.last_page | Preview toolbar | Last page | Icon-only control. |
| dc.a11y.zoom_out | Preview toolbar | Zoom out | Icon-only control. |
| dc.a11y.zoom_in | Preview toolbar | Zoom in | Icon-only control. |
| dc.a11y.preview_pages | Preview thumbnails | Preview pages | Accessibility-only landmark. |
| dc.a11y.rendered_page | PDF preview page | Rendered PDF page preview | Accessibility-only landmark. |

### Strings Not In Scope

| Surface | Example strings | Reason |
|---|---|---|
| File names | `index.html`, `chapter-01.html`, `styles.css`, `cover.png` | User/project data. |
| PDF page content | `Chapter 1`, `Introduction`, table headings, placeholder paragraphs | Represents uploaded source document output. |
| Page and zoom values | `1 / 24`, `100%` | Dynamic preview state. |
| Paper codes | `A3`, `A4`, `A5` | Standard paper-size codes. |

## Package Manifest

The source material below remains authoritative for this section.

## Design Interpretation

The source material below remains authoritative for this section.

## Runtime And Proof Boundary

The source boundaries and recovery limits remain preserved below.

## Governing Links And Follow-Up

The source material below remains authoritative for this section.
