---
type: reference
id: REF-SKRIPT-GENERAL-skola24-timetable-api-for-the-signed-in-teacher
title: Skola24 timetable API for the signed-in teacher
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-20'
status: active
reference_kind: general
summary: 'Undocumented Skola24 web API: endpoints, bodies, selection types, lessonInfo layout and errors, observed from a signed-in Härryda staff session'
---

## Overview

Skola24 has no public API. Its web timetable viewer at `web.skola24.se` calls
a JSON API under `https://web.skola24.se/api/`. This reference records the
calls that return a signed-in teacher's own timetable as structured lesson
records (`lessonInfo`). The planned teacher working-time app imports
timetables from these records.

Scope: the teacher's own timetable on the staff host
`harryda-personal.skola24.se`. The calls were observed on 2026-10-20. They ran
as same-origin `fetch` calls inside the user's signed-in Skola24 tab, so the
browser's own Skola24 session authenticated them. Facts marked "prior art"
come from public open-source clients that use unauthenticated school hosts:

- [klppl/skola24-schema](https://github.com/klppl/skola24-schema)
- [balazshevesi/nar-slutar-lektionen](https://github.com/balazshevesi/nar-slutar-lektionen)
- [VpgMackan/skola24-to-gcal](https://github.com/VpgMackan/skola24-to-gcal)
- [ingobeans/schemavisare-skola24-skolportalen](https://github.com/ingobeans/schemavisare-skola24-skolportalen)

[axelf4/skola24-ripper](https://github.com/axelf4/skola24-ripper) uses a
retired endpoint (`/timetable/timetable-viewer/data/render`) and is obsolete.

## Facts And Semantics

### Access and session

- Härryda staff sign in through Microsoft SAML with MFA. They reach Skola24
  only by opening it from the Microsoft My Apps portal. A headless or
  scripted sign-in is out of scope: no Microsoft credentials are collected
  and MFA is never bypassed.
- Opening a Skola24 deep link without a portal-started session redirects to
  `www.skola24.se/Applications/Core/EndSession.aspx` and ends the session.
  Calls must therefore run inside a tab the user has already opened, and
  that tab must never be navigated.
- Session cookies never leave the browser. Same-origin `fetch` from the
  Skola24 page sends them automatically.
- The page's `Content-Security-Policy` is
  `default-src 'self' * 'unsafe-inline' 'unsafe-eval' data: mailto:; frame-ancestors 'self' *`
  (observed 2026-10-20). It does not block inline script.

### Request conventions

Every call is `POST https://web.skola24.se/api/<path>` with these headers:

| Header             | Value                                                        |
| ------------------ | ------------------------------------------------------------ |
| `Content-Type`     | `application/json`                                           |
| `X-Scope`          | `8a22163c-8662-4535-9050-bc5e1923df48` (web-client constant) |
| `X-Requested-With` | `XMLHttpRequest`                                             |

The viewer also sends `X-Session-ID` when it has one. The calls below
succeed from the page without it. `/api/get/user/info` uses a different
scope, `a0b6c9c4-11d7-4a52-a030-a55a15058eef` (prior art: schemavisare).

Every response has the same envelope: `error`, `data`, `exception`,
`validation` (a list of `{code, message}`), `sessionExpires` and
`needSessionRefresh`. A call succeeded when `error` is `null` and
`validation` is empty.

### Call sequence for the teacher's own week

1. **Personal timetables.** Path
   `/api/services/skola24/get/personal/timetables`, body
   `{"getPersonalTimetablesRequest":{"hostName":"harryda-personal.skola24.se"}}`.
   The response holds `data.getPersonalTimetablesResponse` with the lists
   `teacherTimetables`, `studentTimetables` and `childrenTimetables`. A
   teacher has one `teacherTimetables` entry with the fields `schoolGuid`,
   `unitGuid`, `schoolID`, `signature`, `personGuid`, `firstName` and
   `lastName`.

2. **School year.** Path `/api/get/active/school/years`, body
   `{"hostName":"harryda-personal.skola24.se","checkSchoolYearsFeatures":false}`.
   The response holds `data.activeSchoolYears[]` with `guid`, `name`, `from`
   and `to`. On 2026-10-20 there was one entry, `Innevarande`, running from
   2026-07-01 to 2027-06-30. Pick the entry whose `from`–`to` contains the
   requested week; fall back to the first entry.

3. **Render key.** Path `/api/get/timetable/render/key`, body `null` (prior
   art also sends `{}`). The response holds `data.key`, a 128-character key.
   Fetch a new key for every render call.

4. **Render.** Path `/api/render/timetable`, with this body:

   ```json
   {
     "renderKey": "<data.key from step 3>",
     "host": "harryda-personal.skola24.se",
     "unitGuid": "<unitGuid from step 1>",
     "schoolYear": "<guid from step 2>",
     "startDate": null,
     "endDate": null,
     "scheduleDay": 0,
     "blackAndWhite": false,
     "width": 800,
     "height": 600,
     "selectionType": 7,
     "selection": "<personGuid from step 1>",
     "showHeader": false,
     "periodText": "",
     "week": 43,
     "year": 2026,
     "privateFreeTextMode": false,
     "privateSelectionMode": true,
     "customerKey": ""
   }
   ```

   `week` is the ISO-8601 week and `year` is that ISO week's year. At a year
   boundary these differ from the calendar year: 2026-12-31 falls in week 53
   of 2026, and 2027-01-01 also falls in week 53 of 2026. `scheduleDay` 0
   returns the whole week; 1–7 returns a single day (prior art).
   `width` and `height` size only the drawn grid and do not change
   `lessonInfo`.

The response `data` holds `lessonInfo`, `boxList`, `textList` and
`lineList`. The last three are drawing geometry. `lessonInfo` is `null` when
the week has no lessons (prior art), so treat `null` as an empty list.

### Selection types

| `selectionType` | Selects                 | `selection` value                                 | Evidence                                                                                               |
| --------------- | ----------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| 0               | class                   | `groupGuid` from the selection list               | observed: a class returned 67 lessons in week 42 of 2026; with a `personGuid` it renders an empty grid |
| 3               | room                    | room `eid` from the selection list                | observed: room G20 returned 17 lessons in week 42 of 2026; the room `id` gives `Invalid selection`     |
| 4               | student                 | encrypted signature from `/api/encrypt/signature` | prior art; with a `personGuid` it returns `Felaktigt ID` (observed)                                    |
| 5               | not a room on this host | —                                                 | observed: a room `eid` returns an empty grid, no error; prior-art clients disagree on its meaning      |
| 7               | teacher                 | `personGuid`                                      | observed: returns the teacher's lessons                                                                |

Type 8 with a room `eid` returned the same 17 lessons as type 3; its meaning is
unknown. Types 1, 2, 6 and 9 returned nothing for a room `eid`.

The working-time app uses type 7 for the teacher's own timetable. The
proof-of-concept pull also uses types 0 and 3.

### Lesson record (`lessonInfo[]`)

Each record has the fields `guidId`, `texts`, `timeStart`, `timeEnd`,
`dayOfWeekNumber` and `blockName`:

- `dayOfWeekNumber`: 1 is Monday. The lesson date is the Monday of the ISO
  week plus `dayOfWeekNumber - 1` days.
- `timeStart` and `timeEnd`: local time as `HH:MM:SS`.
- `guidId`: the identifier of a schedule entry, not of one dated
  occurrence. Observed 2026-10-20 over the whole 2026–27 school year and
  three weeks of every teacher, class and room timetable at
  Hulebäcksgymnasiet:
  - The same lesson has the same `guidId` in the teacher, class and room
    views of a week (1,569 of 1,891 class-view entries in week 42 of 2026
    also appear in teacher views; the rest are entries without a teacher).
  - A recurring lesson keeps its `guidId` week after week within a term
    (for example one English lesson kept it for 13 weeks).
  - One-off entries (project-week days, LOV days, single meetings) get a new
    `guidId` each time, and a lesson series can get a new one when the
    timetable changes between terms.
  - A dated occurrence is therefore identified by `guidId` plus ISO year,
    week and `dayOfWeekNumber`.
- `blockName`: an empty string in every record observed on 2026-10-20.
- `texts`: the text lines drawn in the lesson box, in display order. On a
  teacher (type 7) timetable the list has no teacher entry, and its length
  varies with the kind of entry:

| Kind of entry                 | Observed `texts`                                                   |
| ----------------------------- | ------------------------------------------------------------------ |
| Free-text activity            | `["Projektvecka"]`, `["Skolutveckling i arbetslag 8 - 10"]`        |
| Activity with empty fields    | `["Inte på Hulebäck", "", ""]`, `["LUNCH", "", ""]`                |
| Course lesson                 | `["Engelska, nivå 1", "BF26ENGE1000X", "G103"]`                    |
| Course lesson with extra line | `["Engelska 7", " (blocklagt valpaket)", "SA24ENGENG07:2", "G20"]` |
| Several groups                | `["Gymnasiearbete", "SA24GYARSAOla,SA24GYARSAOlof", "G20"]`        |
| Meeting with rooms only       | `["Arbetslagsmöte", "", "H23,H21,H104"]`                           |

Read a record with three or more entries as: the title (the first entry,
plus any middle entries before the last two); the group or groups
(second-to-last entry); and the room or rooms (last entry). Groups and rooms
are comma-separated lists, and either may be empty. A record with one entry
is a free-text activity with no group and no room. Prior-art clients read
`[0]` subject, `[1]` teacher, `[2]` room. That layout belongs to class and
student timetables and does not apply to type 7.

On a class (type 0) timetable the teacher's signature takes the group's
place: `["Ungdomskulturer", " (blocklagt valpaket)", "ABL", "H20"]` reads as
title, extra line, teacher signature and room. The second-to-last entry
therefore depends on the selection type: the group on a teacher timetable
and the teacher on a class timetable.

Records can overlap in time on one day. Week 43 of 2026 had two
"Projektvecka" records on the same day (08:00–17:00 and 09:00–15:00). The API
reports them as separate records; the importer decides how to treat
overlaps.

### Volume and parallel calls

Observed 2026-10-20 with the user's own access (the user approved bulk,
non-abusive use):

- 1,503 renders (all 248 teachers, 114 classes and 139 rooms for three
  weeks) ran 4 calls in flight from the Skola24 page in about 15 minutes,
  with 0 failures, no throttling responses and no session refresh.
- A full school year for one teacher is 53 renders and takes about one
  minute at 4 in flight; ten timetables took a few minutes.
- Each render needs its own key from `render/key` (single-use), so one
  render is two POSTs.
- Keep 4 calls in flight and retry a failed render up to 3 times with a
  short back-off. Stop the batch on `needSessionRefresh`; the teacher must
  reopen Skola24 from My Apps.

### Error messages

| Condition                                      | Result                                                      |
| ---------------------------------------------- | ----------------------------------------------------------- |
| `schoolYear` missing                           | validation message `Ingen läroperiod har valts.` (observed) |
| `selectionType` 0 with a teacher's `signature` | `Invalid selection` (observed)                              |
| `selectionType` 4 with a `personGuid`          | validation message `Felaktigt ID` (observed)                |
| Signed-out or expired session                  | top-level `error` set (prior art: schemavisare)             |

### Other endpoints (not used for the own timetable)

- `/api/get/timetable/selection`: on 2026-10-20 the staff host listed one
  unit (Hulebäcksgymnasiet) with 248 teachers, 114 classes, 139 rooms, 2110
  groups, 280 courses, 286 subjects and no students. Teacher entries have
  `fullName`, `id`, `integrity`, `personGuid` and `selectableBy`; class
  entries `groupGuid`, `groupName`, `selectableBy`; room entries `id` (null),
  `name`, `eid`, `external`, `selectableBy`. `integrity` was `false` for
  every teacher and `selectableBy` was `{"private":false,"staff":true}` for
  every entry.
- `/api/services/skola24/get/timetable/viewer/units`, body
  `{"getTimetableViewerUnitsRequest":{"hostName":"<host>"}}`: lists schools
  as `units[]` with `unitId` (the school name) and `unitGuid`.
- `/api/get/timetable/selection`, body
  `{"hostName":"<host>","unitGuid":"<guid>","filters":{"class":false,"course":false,"group":false,"period":false,"room":false,"student":false,"subject":false,"teacher":true}}`:
  lists selectable `classes`, `teachers`, `rooms` and `groups` for a school.
- `/api/encrypt/signature`, body `{"signature":"<signature>"}`: returns the
  encrypted signature that type 4 needs.

## Decisions And Interpretation

- The importer works from `lessonInfo` only. `boxList`, `textList` and
  `lineList` are drawing geometry; the PDF fallback (pdfplumber geometry) is
  a separate route.
- `personGuid`, `unitGuid`, `schoolYear` and `renderKey` are needed only
  while the calls run. An export for the working-time app carries the
  lesson fields, `week`, `year` and the host. It carries no person, school
  or session identifiers. A re-import diff keys each occurrence on `guidId` plus year, week and
  day; see `guidId` above.
- The API is undocumented and may change without notice. An importer
  validates the shape it receives and rejects anything else; it does not
  guess.
