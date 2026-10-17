---
type: reference
id: REF-SKRIPT-MOCKUP-app-shell-and-exam-workspace-redesign-prototype
title: App shell and exam workspace redesign prototype
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-17'
status: active
reference_kind: mockup
summary: Interactive prototype and design rules for the shared app shell and the exam
  workspace with every current and planned control (TASK-SKRIPT-40-04-01)
---

## Intent

This is the build target for ST-SKRIPT-40-04, made in TASK-SKRIPT-40-04-01. A
teacher opens an exam from the Öppna drawer, corrects the imported questions
in one editor, saves with Spara or Spara som, undoes and redoes up to 10
steps, and exports to a download or to Mina filer. The prototype shows the
shared app shell (top bar, sidebar, page frame) around the exam workspace at
phone, tablet and desktop widths. It covers every current workspace feature
and every planned control in the story's list.

The user approved the prototype on 2026-10-17 (TASK-SKRIPT-40-04-01).
TASK-SKRIPT-40-04-02 builds the shell
and TASK-SKRIPT-40-04-03 builds the workspace. Both follow the
[design rules](#design-rules-for-the-builders) below.

## Package Manifest

The files are in `docs/mockups/app-shell-and-exam-workspace-redesign/`:

| File | Role |
| --- | --- |
| `prototype.html` | Markup for the shell, the workspace, the menus, the dialog and the help panel, plus an inline Lucide sprite (lucide 0.563.0). |
| `styles.css` | Layout, size roles, components and the three breakpoints. |
| `tokens.css` | A byte-identical copy of the huleedu-integrated 0.1.24 `huleedu-design-tokens.css`. |
| `data.js` | Static Swedish example data: question types, courses, central content, saved exams and the open exam with questions 1–14. |
| `app.js` | Behaviour: selection, editing, history, Spara and Spara som, drawers, menus, export and the URL-hash review states. |
| `screenshots/NN-<view>-<width>.png` | 117 PNGs: views 01–27 and 30–39 at `desktop` (1440 × 900), `tablet` (834 × 1112, shown at 1×) and `phone` (390 × 844, shown at 2×), the phone-only views 28 and 29, and `02b-open-drawer-full-desktop` (1440 × 1800, the whole exam list down to Utan kurs). |

Each screenshot is the prototype opened with the hash in the
[review states](#review-states) table. Serve the folder and open the
prototype:

```bash
python3 -m http.server 8765 --bind 127.0.0.1 --directory docs/mockups
```

Open `http://127.0.0.1:8765/app-shell-and-exam-workspace-redesign/prototype.html`.
Add a hash from the table below to open a specific state.

### Review States

| Hash | State | Screenshots |
| --- | --- | --- |
| *(none)* or `q=3` | Question 3: an AI-interpreted key that has not been reviewed | `01-workspace-*` |
| `drawer=open` | Öppna drawer: import box and the exam list grouped by course | `02-open-drawer-*`, `02b-open-drawer-full-desktop` |
| `drawer=open&sort=senaste` | The exam list sorted by date | `37-open-drawer-sorted-by-date-*` |
| `q=3&imp` | The Import box open on question 3, with its steps and Konvertera igen | `03-import-box-*` |
| `q=4` | The instruction, its deluppgifter and the printed-total mismatch | `04-instruction-*` |
| `q=4a` | A deluppgift under the instruction bar, with Bedömningskriterier | `05-child-question-*` |
| `q=5&pop=gap` | Lucktext gap popover: accepted answers, automatisk answers, Visa som text | `06-lucktext-gap-*` |
| `q=7` (`&rgap=N`) | Lucktext med rullista: one option list per gap, one correct option each | `07-rullista-*` |
| `q=8` | Kategorisera grid with points per tick | `08-kategorisera-*` |
| `q=9` | An unbuilt question (Ej konverterad) blocking export | `09-unbuilt-*` |
| `q=10` | A picture in the question and the estimated-points hint | `35-picture-estimated-points-*` |
| `q=4c&menu=more` | A deluppgift's ⋮ menu: Flytta upp, Flytta ned, Ta bort deluppgiften | `36-deluppgift-more-*` |
| `q=11` | A stored suggested type: 'Gör om till Lucktext' | `10-suggested-type-*` |
| `q=12&keepconverting` | A question that is still converting (finishes after 9 s without `keepconverting`) | `11-converting-*` |
| `change=fritext` | Change type: the notice that names the dropped content, with Ångra | `12-change-type-notice-*` |
| `menu=type` | Byt frågetyp menu, with the reserved Ordning entry | `13-type-menu-*` |
| `menu=new` | Ny uppgift menu, with the reserved Ordning entry | `14-new-menu-*` |
| `q=4&menu=child` | + Deluppgift menu, without Ordning | `38-deluppgift-new-menu-*` |
| `q=4a&menu=type` | Byt frågetyp on a deluppgift, without Ordning | `39-child-type-menu-*` |
| `dirty&menu=save` | Osparat status and the Spara split menu | `15-save-menu-dirty-*` |
| `dlg=saveas` (`&err`) | Spara som dialog / with the name already taken | `16-save-as-*`, `17-save-as-name-taken-*` |
| `menu=export` | Export menu with the export blockers | `18-export-menu-blockers-*` |
| `ready&menu=export` | Export menu with no blockers | `19-export-menu-ready-*` |
| `ready&drawer=export&checklist&dest=files` | Export drawer: Spara i Mina filer and the Exam.net checklist | `20-export-drawer-files-*` |
| `drawer=meta` | Provets uppgifter: title, file name, course, central content | `21-meta-drawer-*` |
| `drawer=meta&nocourse&menu=course` | Course search with Mina kurser first | `22-meta-course-search-*` |
| `drawer=meta&othercourse` | A picked course that is not in Mina kurser: Lägg till i mina kurser | `22-meta-other-course-*` |
| `empty` | No exam open | `23-empty-*` |
| `importing` | An import in progress | `24-importing-*` |
| `view=vault` | Mina filer with each exam's exports under it | `25-mina-filer-*` |
| `rail` | Desktop sidebar collapsed to the glyph rail | `26-collapsed-rail-*` |
| `help` | Help panel with the keyboard shortcuts | `27-help-*` |
| `list` | Phone question list | `28-phone-list-phone` |
| `nav` | Phone navigation drawer | `29-phone-nav-phone` |
| `toast=resume` | A suggestion that was running before reload, resumed | `30-resumed-suggestion-*` |
| `ready&toast=qti` | QTI saved to Mina filer, with Visa listan | `31-qti-saved-toast-*` |
| `ready&toast=reviewed` | All questions reviewed, with Exportera | `32-all-reviewed-toast-*` |
| `dirty&drawer=open` | The file picker disabled while edits are unsaved | `33-open-while-unsaved-*` |
| `empty&menu=course` | The course picker at import | `34-import-course-picker-*` |

Other keys: `ready` marks every question reviewed with points; `pref` opens
the type-specific preferences; `sort=senaste` sorts the exam list by date;
`fmt=pdf|docx` picks the export format; `tagsbusy` shows central content
being suggested.

## Design Interpretation

### Layout And Breakpoints

| Width | Shell | Workspace |
| --- | --- | --- |
| Desktop, 1280 px and wider | 56 px top bar; 240 px sidebar with labels; the sidebar toggle collapses it to a 64 px glyph rail | Header row of 60 px; 320 px question list; editor; 380 px drawer docked on the right and narrowing the editor |
| Tablet, 768–1279 px | 64 px glyph rail; Hjälp and Logga ut as glyph-only buttons | 280 px list; header buttons other than Spara are glyph-only; drawers float over the editor with `shadow-md` |
| Phone, below 768 px | Top bar holds the exam title, the save status only (course and total are in Provets uppgifter) and Spara; Meny opens the navigation as a right-side drawer with the user's email, Hjälp and Logga ut | A tool row (Öppna, Exportera, AI, Ångra, Gör om); a question bar with previous, the picker that opens the full-screen list, next, Import and the review check; drawers and the list are full screens with Tillbaka |

### Size Roles

| Role | Size | Used for |
| --- | --- | --- |
| Touch control | 44 px | Every control below 768 px and on coarse pointers |
| Fine control | 36 px | Header and editor buttons on desktop and tablet |
| Compact control | 28 px | Workbench controls inside the editor: mark toolbar, option remove, deluppgift reorder and delete, chip remove |
| `--shell-top` | 56 px | Top bar height |
| `--shell-side` / `--shell-rail` | 240 px / 64 px | Sidebar expanded / collapsed |
| `--ws-head` | 60 px | Workspace header row |
| `--ws-list` | 320 px (280 px on tablet) | Question list |
| `--ws-drawer` | 380 px | Öppna, Exportera and Provets uppgifter drawers |

### Glyphs

Each glyph is a shared-catalogue meaning rendered through `UiGlyph`. The
prototype uses these existing meanings: save, save-to-files, download,
upload, ai-assist, undo, redo, restore, document, retry, move-up, move-down,
delete, add, remove-item, close, confirm, selected, copy, back, previous,
next, open-list, info, status-success, status-warning, status-failure, busy,
status-modified, help, log-out, navigation-menu, settings, account-menu,
choose-from-catalogue, image-file, bold, italic, search, decrement and
more-actions.

The prototype needs these new meanings. The catalogue owner adds them before
the build:

| Proposed meaning | Lucide icon | Where |
| --- | --- | --- |
| `nav-home` | House | Sidebar Hem |
| `nav-files` | Folder | Sidebar Mina filer |
| `open-files` | FolderOpen | Öppna, and the empty state |
| `nav-my-tools` | Wrench | Sidebar Mina verktyg |
| `nav-suggest-tool` | Lightbulb | Sidebar Föreslå verktyg |
| `nav-review-suggestions` | ClipboardCheck | Sidebar Granska förslag |
| `nav-users` | Users | Sidebar Användare |
| `toggle-sidebar` | PanelLeft | Top bar sidebar toggle |
| `instruction` | BookOpen | Instruction rows, the instruction bar, Instruktion med deluppgifter |
| `convert-type` | Replace | 'Gör om till [type]' and the change-type notice |
| `import-file` | FileUp | The Provfil drop zone |
| `export-checklist` | ListChecks | 'Det här tappar Exam.net vid import' |
| `blocker` | CircleAlert | Unbuilt-question line, the export blocker block |
| `underline`, `subscript`, `superscript` | Underline, Subscript, Superscript | Mark toolbar |
| `heading-1`, `heading-2`, `heading-3` | Heading1, Heading2, Heading3 | Mark toolbar |
| `checkbox-on`, `checkbox-off` | SquareCheck, Square | Kategorisera grid ticks in the static markup |

### States And Their Presentation

| State | Presentation |
| --- | --- |
| Saved | Status slot: check glyph and 'Sparat 17 okt 14:05' in muted text |
| Unsaved | The same slot: status-modified glyph and 'Osparat' in warning colour; the tooltip says edits are saved as a draft and Spara overwrites the exam in Mina filer |
| Saving | The same slot: busy glyph and 'Sparar …'; a toast 'Provet är sparat.' follows |
| Undo or redo unavailable | The button is disabled with the tooltip 'Inget att ångra' or 'Inget att göra om' |
| Needs review | List row: warning glyph; a blocker reason in failure colour after the type, such as 'facit ej granskat' or 'poäng saknas' |
| Reviewed | List row: success glyph; the review check in the editor is filled |
| AI-suggested key | Sparkles on the list row and beside the chosen option; 'Facit tolkat av AI ur …' with 'Ångra AI-tolkningen' |
| Suggestion out of date | A dot on the Alternativ Sparkles button |
| Suggesting for all questions | The header AI button shows busy and is disabled; after a reload the run resumes with a 'Facitförslagen tas fram …' toast |
| Unbuilt question | Type button in failure colour 'Ej konverterad' and one failure line under the header |
| Converting | Muted list row with busy glyph; a warning-surface notice; read-only fields |
| Export blocked | The export menu starts with 'Kan inte exporteras ännu' and links to each blocking question; the format rows are disabled |
| Total mismatch | Warning glyph on the instruction row and 'Provet anger 60 p' in the list footer |
| Picker disabled while unsaved | Course, drop zone and Välj provfil are disabled, with 'Spara det öppna provet innan du importerar eller öppnar ett annat.' |
| No exam open | Header 'Inget prov öppet'; every action except Öppna is disabled; the editor shows the empty state; the Öppna drawer opens |
| Importing | The drop zone becomes a progress card: 'Konverterar provet: 4 av 12 frågor klara.' |

### Design Rules For The Builders

1. **One composition per width.** Each width has the layout in the table
   above. Controls stay on their row; text that does not fit truncates with
   an ellipsis, and the full text is in the tooltip.
2. **The layout holds still.** A state change alters the glyph, colour,
   pressed or expanded state, or disabled state. It never moves a
   neighbouring control. The status slot is sized for 'Sparat 17 okt 14:05',
   so 'Osparat' and 'Sparar …' leave the course and total where they were.
   On phone the status line shows only the save status.
   The Import box opening above the fields is the one change that moves
   content.
3. **Spara is the only filled action in the view.** Spara som is in the
   split menu. In the dialog, 'Spara kopia' is the filled action because the
   dialog replaces the view.
4. **Glyph first, one word where needed.** Header buttons show a glyph and
   one word on desktop (Öppna, Spara, Exportera) and only the glyph below
   1280 px, except Spara. The AI, Ångra and Gör om buttons are glyph-only at
   every width. The action phrase is in the tooltip and accessible name, with
   the shortcut where there is one ('Ångra (⌘Z)').
5. **Surfaces.** Flat surfaces have no shadow. Menus, popovers, floating
   drawers, toasts and the dialog use `shadow-md`. The scrim dims the page
   only under the dialog and the phone navigation drawer.
6. **Colour roles.** Terracotta is used only for 'Provredigering'. Teal
   `action` is for the filled Spara, selection, pressed states and the
   current navigation item. Failure red marks a blocker reason. Warning
   orange marks needs-review and unsaved. Success green marks reviewed.
7. **Where each control lives.** Exam-level actions are in the header.
   Question-level actions are in the question header: type, 'Gör om till',
   Import, review, ⋮. Field-level actions sit at their field: + Alternativ,
   + Lucka, + Kriterium, + Deluppgift, remove. Exam properties are in
   Provets uppgifter, which the exam title opens.
8. **Notices.** A change that removed content shows a toast that names
   what was removed and offers Ångra. It stays until it is closed. Short
   confirmations close by themselves after about 4 s.
9. **Keyboard.** Ctrl/Cmd+S runs Spara. Ctrl/Cmd+Z and Ctrl/Cmd+Shift+Z
   undo and redo, including inside text fields. Up and down arrows outside a
   text field move between list rows; inside an open menu, the arrows, Home
   and End move between its enabled items and skip disabled ones. Escape
   closes the top layer: the dialog, then the gap popover, then an open menu,
   then the drawer. Enter confirms the dialog. The help panel lists these
   shortcuts.
10. **History.** One step is one autosave: a structural edit or a pause of
    900 ms in typing. At most 10 steps are kept. A Spara does not clear the
    history. Spara som starts the copy's history empty.
11. **Reorder within the parent only.** Deluppgifter move up and down inside
    their instruction. The last deluppgift cannot be deleted; its delete
    button is disabled with 'En instruktion behöver minst en deluppgift'.
12. **Fine-pointer reveal.** Option remove buttons show on hover or focus on
    fine pointers and are always visible on touch.
13. **Reserved entry.** 'Ordning' sits last among the types in Byt frågetyp
    and Ny uppgift. + Deluppgift, and Byt frågetyp on a deluppgift, omit it,
    because an ordering question is standalone only (ST-SKRIPT-39-06 P3).
    The entry is `aria-disabled`, cannot be chosen, is out of the tab order
    and skipped by the menu arrows. Its hint 'Kommer senare' is small muted
    text at the row's end on every device, linked through
    `aria-describedby`; it has no tooltip, because touch shows none. The entry
    is removed if the TASK-SKRIPT-39-06-02 decision drops ordering.

### Binding And Illustrative

Binding: the layout and breakpoints, the size roles, where each control
lives, the glyph meanings, the state presentation and the rules above.
Illustrative: the example questions, course list, central content, file
names, dates and times, the export file names, and the timings the prototype
fakes (the save toast and the 9 s conversion).

## Controls Coverage

| Control (ST-SKRIPT-40-04) | Where it lives | Screenshot |
| --- | --- | --- |
| Top bar, sidebar, page frame | Shell | `01`, `26`, `29` |
| Estimated-points hint | Poäng row of question 10 | `35` |
| Unbuilt-question blocker | Question header and list row | `09` |
| Exam and part total mismatch | List footer, instruction row and instruction editor | `01`, `04` |
| Course hint | Provets uppgifter under Kurs ('Ämne: Svenska') | `21` |
| Per-question Konvertera igen | Import box, with the type select | `03` |
| Pictures in questions | Frågetext of question 10 | `35` |
| Undo an AI-interpreted key, with the original facit | 'Facit tolkat av AI ur …' + 'Ångra AI-tolkningen' | `06` |
| Automatisk misspellings and Visa som text | Gap popover | `06` |
| Mark toolbar | Above every rich field | `01` |
| Kategorisera grid with points per tick | Answer section of question 8 | `08` |
| Fritext criteria | Bedömningskriterier | `05` |
| Kort svar under Ny fråga | Ny uppgift menu | `14` |
| Export checklist after QTI | Export drawer and the QTI toast | `20`, `31` |
| Metadata drawer opened from the exam title | Title button → Provets uppgifter | `21` |
| Course picker at import | Öppna drawer, Kurs (valfritt) | `34` |
| File picker disabled while unsaved | Öppna drawer | `33` |
| Pending suggestion resumed after reload | Header AI button + toast | `30` |
| Öppna drawer exam list: by course, newest first, sort toggle, Utan kurs | Öppna drawer, Prov | `02`, `02b` (shows Utan kurs), `37` |
| Spara and Spara som | Header split button; dialog | `15`, `16`, `17` |
| Undo and redo, 10 steps, shortcuts | Right end of the header; help panel | `12`, `15`, `27` |
| Ctrl/Cmd+S | Spara tooltip, Spara menu, help panel | `15`, `27` |
| Import box with steps, DOCX and DigiExam | Question header Import → inline box | `03` |
| Change type with the dropped-content notice | Type button → Byt frågetyp; toast with Ångra | `13`, `12` |
| Gör om till [type] | Question header of question 11 | `10` |
| Ny uppgift and + Deluppgift | List header; Deluppgifter heading | `14`, `04` |
| Add, delete and reorder deluppgifter | Instruction editor rows; ⋮ on a deluppgift | `04`, `36` |
| Dropdown Lucktext | Rullistor cards per gap, radio key, 'Rätt svar' | `07` |
| DigiExam import entry | Provfil drop zone chip 'DigiExam .dxe'; DigiExam chip on the exam row | `02`, `24` |
| Central content checklist | Provets uppgifter, Centralt innehåll | `21`, `22-meta-other-course` |
| Lägg till i mina kurser | Under the picked course in Provets uppgifter | `22-meta-other-course` |
| Exports saved to Mina filer, one per format, shown next to the exam | Export menu save-to-files buttons; export drawer Mål; exam rows; Mina filer | `19`, `20`, `02`, `25` |
| Ordering question | A disabled 'Ordning' entry reserves its place in Byt frågetyp and Ny uppgift; + Deluppgift and Byt frågetyp on a deluppgift omit it (TASK-SKRIPT-40-04-01 T28, ST-SKRIPT-39-06 P3) | `13`, `14`, `38`, `39` |

## Runtime And Proof Boundary

The prototype is static. It cannot show the server-side history surviving a
reload, real autosave timing, real conversion progress, the real export
files or the size of the Mina filer index. Those belong to the Sol lanes in
ST-SKRIPT-39-04, 39-06, 39-07 and 39-08. TASK-SKRIPT-40-04-02 and
TASK-SKRIPT-40-04-03 own building to this prototype and proving it in a real
browser. The lead checks their screens against the screenshots here.

## Governing Links And Follow-Up

- Story: ST-SKRIPT-40-04. Task: TASK-SKRIPT-40-04-01 (records the user's
  approval).
- Earlier prototype:
  REF-SKRIPT-MOCKUP-exam-workspace-editor-with-drawers-prototype.
- Approved looks:
  REF-SKRIPT-MOCKUP-exam-workspace-approved-mockups-for-the-shared-design-direction.
- Planned-control contracts: ST-SKRIPT-39-06 (P13, P15),
  TASK-SKRIPT-39-06-02 to 39-06-06, TASK-SKRIPT-39-07-01,
  TASK-SKRIPT-39-08-02 to 39-08-04, TASK-SKRIPT-39-04-06 and 39-04-08.

The user settled the prototype's 23 open questions in the 2026-10-17
grilling. They are TASK-SKRIPT-40-04-01's Decided Contract Terms T6–T28; T29
records the later touch-hint decision. This document and the prototype follow
them. The user approved the prototype on 2026-10-17, recorded in that task.
