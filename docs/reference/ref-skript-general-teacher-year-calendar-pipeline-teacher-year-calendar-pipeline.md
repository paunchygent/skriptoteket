---
type: reference
id: REF-SKRIPT-GENERAL-teacher-year-calendar-pipeline
title: Teacher year calendar pipeline
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-20'
status: draft
reference_kind: general
summary: 'How Skriptoteket turns a teacher''s Skola24 timetable and the school kalendarium into an Outlook year calendar: extension, deduction, questionnaire, base schedule, ICS delivery.'
---

## Overview

Skriptoteket builds one Outlook calendar file (ICS) per teacher and school
year. It combines the teacher's own Skola24 timetable, the school's
kalendarium (läsårskalender) and the teacher's duties. The file imports
into the teacher's main Outlook calendar, which is the calendar Teams shows.
Olof Larsson's 2026/27 calendar was built this way by an agent on
2026-10-20; the agent method is the HuleEduOS skill
`.codex/skills/arsplanering-outlook/`. This reference describes the same
pipeline as an app feature. The Skola24 calls are in the
[Skola24 timetable API reference](ref-skript-general-skola24-timetable-api-for-the-signed-in-teacher-skola24-timetable-api-for-the-signed-in-teacher.md);
the import-client choices (D1–D12) are in the
[import client decisions](ref-skript-decisions-skola24-timetable-import-client-decisions-2026-10-20-skola24-timetable-import-client-decisions-2026-10-20.md).

## Facts And Semantics

### Pipeline

1. **Read the timetable** in the teacher's signed-in Skola24 tab: the own
   timetable for every ISO week of the active school year (53 renders,
   selection type 7). Weeks are computed from midnight UTC.
2. **Send it to the backend** together with the school year and teacher
   signature. The export carries no session cookie or credential.
3. **Deduce** what the timetable already answers (below).
4. **Ask** only what is left (below).
5. **Select** kalendarium items for the teacher and apply exclusions, moved
   entries and away days.
6. **Return the ICS** with stable UIDs. The teacher imports it through
   Outlook on the web.
7. **Update** on a later export: the backend diffs against the previous
   export and returns the changed events and a separate file of new events.

### Sign-In And Access

- Härryda staff reach Skola24 only through the Microsoft My Apps portal
  (SAML and MFA). A direct Skola24 deep link ends the session.
- On a work laptop signed in with the Härryda account, Edge is usually
  signed in to Microsoft (single sign-on), so My Apps and Skola24 open
  without a prompt. On a private computer the teacher signs in with MFA.
- The extension therefore asks one question first: "Har du Skola24 öppet i
  en flik?" If not, it tells the teacher to open Skola24 from My Apps, and
  waits. It never opens a Skola24 URL itself.
- The extension calls the Skola24 API from the Skola24 page (same origin)
  with the page's session; the backend never sees the session.
- Open check: whether Härryda's Edge policy allows installing a private
  extension on work laptops (the user checks). Fallbacks: bookmarklet,
  then console paste (D-ledger).

### Extension v1: Two Parts

- **Part 1, Skola24 reader** (content script on `web.skola24.se`): pulls the
  year as above and posts it to the Skriptoteket import page in an open
  window (`postMessage`, origin pinned to `https://web.skola24.se`).
- **Part 2, questionnaire and delivery** (Skriptoteket page): shows what was
  deduced, asks the remaining questions, previews the selection, and
  downloads the ICS.

### What The Timetable Answers

| Fact                                         | How it is deduced                                                              |
| -------------------------------------------- | ------------------------------------------------------------------------------ |
| Courses and groups                           | Teacher-view texts: title, group, room                                         |
| Subjects → ämneskonferens slot               | Course title → subject → ÄK1/ÄK2/ÄK3 list on the kalendarium's last page       |
| Year groups taught                           | Group names (SA24 = year 3 in 2026/27, BF26 = year 1)                          |
| Programme                                    | Majority programme prefix of the groups (SA, BF, NA …)                         |
| Mentor class                                 | `MENTORSTID … <klass>` entries                                                 |
| National tests that hit the teacher's groups | NP items whose audience matches a taught group and course                      |
| Away days                                    | Entries such as "Inte på Hulebäck"; whole-day gaps                             |
| Events already in Skola24                    | Same-date Skola24 entry with the same meaning; the kalendarium item is skipped |

### What Must Be Asked

The timetable cannot show duties from the tjänstefördelning, and it shows
programme-wide entries that only some teachers hold.

- Design rule: one screen of tick boxes, "Kryssa i det som gäller dig".
  Unticked means no. Fewer clicks than asking about each item.
- Skip any question whose answer follows from another: no mentor entry →
  no mentor questions; no modern-language course → no Språkdag question;
  a single ÄK → no ÄK choice.
- Ask for typed input only when it is worth it: a booked day for a shared
  event (GY-mässan), a moved lesson with its new time.
- Questions (Swedish in the UI):
  - Uppdrag i tjänstefördelningen: Enhetsråd, Verksamhetsråd,
    Skolutvecklingsråd, Stora digitaliseringsgruppen, Marknadsföring
    (mässor, öppet hus), Studiepass, Facklig medlem.
  - Programme-wide Skola24 entries the teacher does not run (Studiepass,
    Programråd): untick to remove.
  - National tests the teacher runs, from the deduced list.
  - Recurring meetings the teacher attends only when possible (tentative).
  - Changes not yet in Skola24: "Har något i ditt schema ändrats som inte
    syns i Skola24 än?" Asked at every export.

### Base Schedule (Step After v1)

The teacher's base schedule (arbetstidsschema: days and hours at Hulebäck)
gives away days and working hours. It comes from the backend when the
teacher has entered it, or from the completed Excel file the teachers
already use, read by the backend. Away time becomes a busy double booking,
and school meetings inside it become tentative.

### Working-Time Form (Decision, 2026-10-20)

- The form first asks whether the teacher uploads the arbetstidsschema
  2026/27: the default workbook template from Teams, unchanged in format
  ("IDA MALL 2627 Arbetstidsschema Gymn Original 260522.xlsx"). The upload
  answers working days, working hours and away time; the form asks none of
  those again.
- Only a teacher who does not upload gets the fallback questions, in free
  text. The backend turns each answer into small parts (yes/no, weekdays,
  time intervals, reason) with the same classifier route as the exam
  converter (OpenAI Decisions API with probabilities, see
  ST-SKRIPT-39-05) and a prompt of its own, then parses those parts
  deterministically.
- Everything else is fixed choices: duties from the tjänstefördelning, and
  meetings attended only when possible, listed from the kalendarium.
- The form is tested with synthetic teachers first (labelled synthetic,
  built from known colleagues' Skola24 data and duties) and then with one or
  two real test answers that are deleted afterwards.

### Agreed Away Time And Working Time

- Agreed away time (research studies, another employer) wins over the school
  schedule. One busy event covers it and reuses the Skola24 entry's UID.
- Important school events inside the away time stay visible as free with a
  note: Projektvecka, national tests and exams for the teacher's groups and
  class. The teacher has a substitute but must know about them. The app never
  drops them.
- Meetings running past the away time stay tentative.
- Working time from the arbetstidsschema becomes one free event per working
  day at school; away days need no second working-time event.

### ICS Contract

- `METHOD:PUBLISH`, UTC times, all-day events with `VALUE=DATE`.
- UIDs: `s24-<guidId>-<yyyymmdd>@<domain>`, `kal-<item id>@<domain>`,
  `away-<yyyymmdd>@<domain>`. An occurrence keeps its UID across exports.
- Show-as through `X-MICROSOFT-CDO-BUSYSTATUS` (BUSY, TENTATIVE, FREE) and
  `TRANSP`. All-day banners are FREE.
- Categories: Skola24, Kalendarium, Frånvaro.

### Outlook Delivery Quirks (Observed 2026-10-20)

- Outlook on the web "Ladda upp från fil" imports into the main calendar
  and updates events with a known UID instead of duplicating them.
- A full re-import updated existing events but did not create events with
  new UIDs. New events must be delivered as a second, small file.
- An import never deletes. A re-imported event with `STATUS:CANCELLED`
  stays unchanged. Removed events must be deleted in Outlook; the app lists
  them for the teacher.
- About 600 events take about two minutes to import.
- Microsoft Graph calendar write needs admin consent in the municipality
  tenant; an ICS subscription needs a public URL, refreshes every 6–24 h
  and lands in a separate calendar that Teams does not show.

### Shared Kalendarium Rules

- Item classes (all staff, breaks, ämneskonferens, course and test, year
  group, mentor, duty, modern languages, already in Skola24,
  administrative) and their rules are in the HuleEduOS skill reference
  `kalendarium-mapping.md`.
- The kalendarium omits the Christmas break weekdays; the app adds a JULLOV
  banner.
- The 2026/27 machine-readable kalendarium is in retained root
  `01a1584c-0861-7cdd-a0df-3822e122c44a`; its `subject_conferences` field is
  empty and must be filled from page 7 before the app uses it.

### Target Architecture (Proposal, 2026-10-20)

Olof Larsson's proposal to the principals and the head of upper secondary
education:

- One package gathers four sources in one place: the tjänstefördelning,
  the Skola24 year timetables, the kalendarium and the arbetstidsschema.
  Every teacher then sees a complete year without assembling it by hand.
- The kalendarium keeps its PDF. A machine-readable version is updated
  automatically whenever the PDF is updated, through a small add-on that
  Olof provides.
- With Microsoft Graph access, the package reads no timetable through a
  browser extension and writes each teacher's Outlook calendar directly.
  Without it, the extension and ICS route in this reference is the
  fallback.
- Decisions are entered once in Härryda's internal low-code app platform
  (JSON, Python and JavaScript scripts); calendars update from there.
- The package is open source on GitHub, runs in any hosting environment,
  and connects through adapters (Skola24, kalendarium, tjänstefördelning,
  arbetstidsschema, calendar delivery), so municipal IT can download and run
  it with minimal integration. Olof's own hosting serves only as a
  demonstration.
- Open question: whether Skola24 offers an official integration that the
  municipality can use instead of the signed-in browser read.

### Power Automate Delivery (Proposal, 2026-10-20)

The proposal depends on one gate, which is not yet verified. An instant flow
owned by Olof is shared with teachers as run-only users. The Office 365
Outlook connection is set to "provided by run-only user", while the data
connection stays Olof's. A teacher's Run then writes the teacher's own
calendar.

- Gate checks, read-only first, in Härryda's portal:
  - the Share page offers run-only users;
  - the Outlook connection can be provided by the run-only user;
  - no data policy blocks Outlook in that mode;
  - whose request budget a run-only run uses (Low profile: 10,000 requests
    per 24 h).
- If the gate passes:
  - The builder (outside Microsoft) writes one event table per teacher to
    OneDrive or SharePoint.
  - The teacher's Run syncs the calendar: it creates, updates and deletes
    only events carrying the flow's own key and category. The connector
    cannot set `iCalUId`.
  - The teacher signs in to the connection once, then clicks once per
    update. Deletions are included, which the ICS route cannot do.
- A Forms trigger runs under Olof's connection. It can read answers and
  uploads, but it cannot write a respondent's calendar. Form delivery is
  therefore two stages: an Olof-owned processing flow, then the teacher's
  own Run.
- Before relying on them, check:
  - whether Office Scripts ("Run script") is enabled in the tenant, to read
    the arbetstidsschema workbook (Excel Online reads only defined tables);
  - whether Power Apps is available.
- A Microsoft Lists working-time list in Teams can replace the Excel
  workbook:
  - per-row validation lives in the list;
  - sums over the beräkningsperiod (reglerad arbetstid) live in a flow,
    which writes a status column back.
- Calendars already loaded through ICS must not be duplicated. Either the
  first flow run removes the ICS events, or the flow manages only its own
  events.
- Stays outside Microsoft:
  - reading Skola24 (signed-in browser, no API);
  - the builder;
  - kalendarium parsing;
  - the classifier (the HTTP connector is premium).
- One-click start (user requirement, 2026-10-20): the teacher starts the
  update from a button in the Edge extension. The extension opens the
  shared flow's run page, so the teacher clicks the button and then Run.
  A flow cannot be started directly from outside the portal without the
  HTTP trigger, which is premium. Olof checks on 2026-10-21 whether a
  private extension installs on the work laptop.
- If the gate fails, ICS stays the delivery route.

### Shared Exam Schedule (Proposal, 2026-10-20)

The last module of the same package: one exam schedule for the whole
school, replacing the separate OneNote, Excel and Word schedules that the
14 student teams mirror on their Teams pages.

- **Rule check on entry**: maximum tests per class and day, subject
  exceptions, weeks closed to tests (such as the language week) and which
  tests those weeks allow. A conflict is shown before the test is saved.
- **Student view**: one page per class, filled automatically and mirrored on
  the class's Teams student-information page. Students do nothing.
- **Teacher view**: every test week of the school year with each test's
  class, subject and content.
- **Entry with minimal input**: the signed-in teacher is known, so no name.
  Class and subject are picked from the teacher's own timetable groups and
  subjects. The test description is the only typed field. The teacher
  picks the day; the app proposes the teacher's own lesson with that class
  on that day, and the teacher confirms it.
- Tests reach the teacher's calendar through the same ICS or Graph
  delivery as the rest of the year.

## Decisions And Interpretation

- The questionnaire asks the teacher to tick what applies; anything
  unticked is excluded (user decision 2026-10-20).
- Demo files for colleagues without answers keep Studiepass and other
  programme-wide entries; the teacher deletes what does not apply (user
  decision 2026-10-20).
- Deduction runs before questions; the questionnaire shows deduced facts
  for confirmation rather than asking for them.
- Implementation needs a backlog item before any code; this reference is
  the input to that planning.
