# Grundplan för hela plattformen

En **grundplan för hela plattformen** enligt exakt samma struktur genom hela kedjan: **PRD (inkl. design specs) → ADR → Epics → Stories**. Jag skriver detta som ett “v0.1–v1.0 foundations-paket” som ni kan lägga i repo som `/docs/` och driva arbetet från.

Obs! Detta är en grundplan för hela plattformen, inte en specifik implementering. BLOCKERAD tills doc_structure_requirements.md är klar.

---

## A. Arbetsmodell och artefakter

### A1. Repo-struktur för planeringen

Rekommenderad dokumentstruktur:

```text
docs/
  prd/
    prd-script-hub-v0.1.md
    prd-script-hub-v1.0.md
  adr/
    adr-000-template.md
    adr-001-ui-server-driven.md
    adr-002-tool-as-folder.md
    ...
  backlog/
    epics.md
    stories/
      epic-01-tool-registry.md
      epic-02-ingest.md
      ...
  runbooks/
    operations.md
    security.md
    tool-authoring.md
```

### A2. Definition of Ready och Definition of Done

**Definition of Ready (DoR) för en Story**

* Problem/nytta uttryckt som “Som … vill jag … så att …”
* Acceptance Criteria finns och är testbara
* Risk/beroenden noterade (minst “none” om inga)
* UI-impact: “none / template / form / partial / page”
* Data-impact: “none / job storage / retention / PII”

**Definition of Done (DoD)**

* Implementerad + kodgranskad
* Tester: minst enhetstest eller integrationstest enligt story-typ
* Fel- och edge-cases hanterade (validering, storlek, felmeddelanden)
* Loggning och observability: relevant logg + ev. metric
* Dokumenterad i `tool-authoring.md` eller relevant README
* Säkerhetskontroll: inga osäkra exekveringar / korrekt filhantering

---

## B. PRD v0.1 — Script Hub Foundations

### B1. Sammanfattning

En intern webbaserad “Script Hub” där användare kan välja ett verktyg, ladda upp filer (xlsx/csv/docx/pdf/md/py) och få resultat som HTML samt ev. nedladdningsbara artefakter, med låg friktion och hög driftstabilitet.

### B2. Mål och mätetal

**Mål**

1. Göra verktyg körbara via web UI utan att användare behöver Python.
2. Standardisera fil-ingest så verktyg blir enkla att skriva och granska.
3. Minimera drift- och underhållskomplexitet.

**Success metrics**

* TTFX (“time-to-first-result”) för standardjobb: < 5 sek (lokal/normal last, icke-LLM)
* Andel lyckade körningar: > 95% (exkl. felaktiga filer)
* Nytt verktyg från mall till “körbart”: < 30 min för en utvecklare

### B3. Personas och primära use cases

**Persona A: Lärare (icke-teknisk)**

* Väljer tool → laddar upp fil → får tydlig output → laddar ner resultat.

**Persona B: Tool-författare (semi-teknisk)**

* Skapar tool-katalog → skriver `tool.yaml` + `tool.py` → får UI “gratis” → publicerar via PR.

**Use cases (MVP)**

* UC1: Ladda upp CSV/XLSX och få transform/summering
* UC2: Ladda upp PDF/DOCX och få extraherad text + förenklad sammanfattning
* UC3: Ladda upp `.md`/`.py` som text (ingen körning)

### B4. Scope

**In scope (v0.1)**

* Tool registry och tool-sidor
* Filuppladdning och ingest (pdf/docx/csv/xlsx/md/py)
* Synkron körning
* Resultat renderas i HTML-partial
* Grundläggande felhantering

**Out of scope (v0.1)**

* Asynkron kö (Celery/RQ)
* OCR för skannade PDF:er
* Multi-tenant eller avancerad behörighetsmodell
* Exekvering av uppladdad kod

### B5. Funktionella krav (FR)

* **FR-001 Tool Listing:** Systemet listar alla tools med namn/description.
* **FR-002 Tool Detail Page:** Varje tool har en sida med uppladdningsformulär.
* **FR-003 File Upload:** Användare kan ladda upp 1 fil per körning (v0.1).
* **FR-004 Ingest Normalization:** Systemet normaliserar fil → `IngestedFile` (text/tabell som text).
* **FR-005 Run Tool:** Tool kan köras med `entrypoint`.
* **FR-006 Result Render:** Resultat returneras och renderas i result-yta.
* **FR-007 Errors as UI:** Fel presenteras som användarvänlig HTML, inte stacktraces.

### B6. Icke-funktionella krav (NFR)

* **NFR-001 Security:** Ingen exekvering av uppladdad `.py`.
* **NFR-002 Size Limits:** Max storlek per fil konfigurerbar (t.ex. 25 MB).
* **NFR-003 Accessibility:** Formulär och resultat ska fungera med tangentbord och utan JS.
* **NFR-004 Observability:** Logga job-id, tool-id, filtyp, duration, status.
* **NFR-005 Portability:** Körbart lokalt och på en enkel server (single node).
* **NFR-006 Data retention:** Jobbfiler rensas enligt policy (t.ex. 7–30 dagar).

---

## C. PRD Design Specs (UI/UX) v0.1

### C1. Informationsarkitektur

* `/` Lista tools
* `/tools/{tool_id}` Tool-sida
* `/tools/{tool_id}/run` POST, returnerar partial HTML

### C2. UI-komponenter (standard)

1. **Tool Header**

   * Name, description
2. **Upload Form**

   * Fil-input (required)
   * Valfritt textfält “Instruktion”
   * Submit-knapp
3. **Result Panel**

   * Status (success/error)
   * Job-id
   * Resultat HTML
4. **Error Panel**

   * “Vad gick fel”
   * “Hur du kan lösa det” (typiska åtgärder)

### C3. Interaktionsspec (HTMX)

* Submit sker via `hx-post`
* Resultat ersätter `#result` via `hx-swap="innerHTML"`
* Vid fel returneras samma partial men med error-state

### C4. Tomma och fel-lägen

* Tomt resultat: visa “Kör ett jobb för att se resultat”
* Ogiltig filtyp: “Den här filtypen stöds inte av verktyget”
* Extraktionsfel: “Kunde inte läsa filen. Prova att spara om som …”
* Timeout (senare): “Jobbet tog för lång tid …”

---

## D. ADR-katalog — Grundbeslut

Nedan är ett rekommenderat ADR-set. Varje ADR skrivs som ett kort dokument med: Kontext → Beslut → Alternativ → Konsekvenser.

### ADR-000 Template

* Rubrik, datum, status (Proposed/Accepted/Superseded)
* Kontext
* Beslut
* Alternativ
* Konsekvenser
* Uppföljning

### ADR-001 UI: Server-driven + HTMX

**Beslut:** Serverrenderad HTML + HTMX för partial-uppdateringar.
**Konsekvens:** Minimal JS, enklare forms, bättre driftsäkerhet.

### ADR-002 Backend: FastAPI + Jinja2

**Beslut:** FastAPI för routing + Jinja2 för templates.
**Konsekvens:** Enkel, tydlig separation mellan UI och körlogik.

### ADR-003 Packaging: PDM + src-layout

**Beslut:** PDM managed, `src/` layout.
**Konsekvens:** Reproducerbar miljö, tydlig modulstruktur.

### ADR-004 Tool distribution: “Tool-as-folder”

**Beslut:** `src/hub/tools/<tool_id>/` med `tool.yaml` och `tool.py`.
**Konsekvens:** Enkelt att bidra via PR och att granska.

### ADR-005 Contract: tool.yaml schema

**Beslut:** Deklarativt schema för metadata, accept, inputs, limits.
**Konsekvens:** Stabilt kontrakt; UI kan genereras eller standardiseras.

### ADR-006 Ingest pipeline

**Beslut:** Central ingest som normaliserar till text/tabell/text.
**Konsekvens:** Tools blir små och konsistenta.

### ADR-007 Storage: Filesystem per job

**Beslut:** Jobb skapar katalog på disk, lagrar upload + outputs.
**Konsekvens:** Enkelt i single-node. Kräver retention-policy.

### ADR-008 Execution model v0.1: Synkront

**Beslut:** Kör tools synkront i request-cykeln initialt.
**Konsekvens:** Enkelt men begränsar långkörningar.

### ADR-009 Execution model v0.2+: Asynkron option

**Beslut:** Förbered gränssnitt för senare kö (RQ/Celery).
**Konsekvens:** Ingen ombyggnad av tool-interface.

### ADR-010 Security: No user code execution

**Beslut:** `.py` ingest som text. Ingen eval/import av uppladdat.
**Konsekvens:** Minskad risk, högre förutsägbarhet.

### ADR-011 Auth (framtid)

**Beslut:** v0.1 utan auth eller via reverse proxy; v0.3 intern auth.
**Konsekvens:** Snabb MVP, planerad hardening.

### ADR-012 Observability

**Beslut:** Structured logging med job-id/tool-id + timings.
**Konsekvens:** Felsökning blir möjlig utan att exponera data.

---

# E. Epics → Stories

Nedan är en full “foundation backlog” som täcker plattformen från första körbara MVP till stabil v1.0. Varje story har tydliga acceptance criteria och levererar mätbar nytta.

---

## Epic 01 — Platform Skeleton & Configuration

**Mål:** Körbar applikation med config, templates, statics, PDM.

### Story 01.1 — PDM project scaffold

**Som** utvecklare **vill jag** ha en PDM-managed projektstruktur **så att** miljön blir reproducerbar.
**AC**

* `pyproject.toml` med dependencies + dev scripts
* `src/` layout
* `pdm run dev` startar server

### Story 01.2 — Settings via environment

**AC**

* `.env.example` och `settings.py` (data_dir, max_upload_mb)
* Defaults fungerar utan `.env`

### Story 01.3 — Base templates & static pipeline

**AC**

* `base.html`, `index.html`, `tool.html`, `partials/result.html`
* CSS kan serveras från `/static/`

---

## Epic 02 — Tool Registry & Discovery

**Mål:** Tools hittas, valideras och exponeras i UI.

### Story 02.1 — Load tool.yaml from tools directory

**AC**

* Ignorera kataloger utan `tool.yaml`
* Tool måste ha `id`, `entrypoint`
* Fel i YAML loggas och tool inaktiveras

### Story 02.2 — Registry cache at startup

**AC**

* Registry laddas vid start
* `/` visar tools från registry

### Story 02.3 — Tool detail routing

**AC**

* `/tools/{tool_id}` returnerar 404 om tool saknas
* Visar name + description

---

## Epic 03 — Tool Contract & Authoring SDK

**Mål:** Stabilt kontrakt och enkel verktygsutveckling.

### Story 03.1 — tool.yaml schema v0.1

**AC**

* Fält: `id`, `name`, `description`, `entrypoint`, `accept`, `limits`
* `accept` valideras som lista av filändelser

### Story 03.2 — Tool runtime interface

**AC**

* Tool entrypoint signatur standardiseras:

  * `run(ing: IngestedFile, params: dict, job_dir: Path) -> ToolResult`
* `ToolResult` kan bära `html` + `output_files`

### Story 03.3 — Tool author guide

**AC**

* `docs/runbooks/tool-authoring.md` med:

  * minimalt exempel
  * hur man deklarerar accept/limits
  * hur man skapar outputfil

---

## Epic 04 — Upload, Validation & Limits

**Mål:** Robust filuppladdning, tydlig validering.

### Story 04.1 — Multipart upload handling

**AC**

* Form klarar fil + textfält
* Fil sparas i job_dir

### Story 04.2 — File type allowlist per tool

**AC**

* Om filändelse ej finns i tool.accept → användarvänligt fel

### Story 04.3 — Size limit enforcement

**AC**

* Om fil storlek > max_upload_mb → avbryt med tydligt fel
* Logga försök med tool-id

---

## Epic 05 — Ingest & Extraction

**Mål:** Normalisera filer till text/tabell i enhetligt format.

### Story 05.1 — CSV extraction

**AC**

* CSV läses, normaliseras till text (t.ex. CSV-sträng)
* Hantera encoding errors med fallback (replace)

### Story 05.2 — XLSX extraction

**AC**

* Läser första sheet default (v0.1)
* Konverterar till CSV-sträng

### Story 05.3 — DOCX extraction

**AC**

* Sammanfoga paragrafer till text
* Tomt dokument ger tydligt fel eller tom-text med varning

### Story 05.4 — PDF extraction (no OCR)

**AC**

* Extraherar text från sidor
* Om ingen text hittas: tydlig varning “PDF verkar vara skannad”

### Story 05.5 — MD/PY extraction

**AC**

* Läs som text
* Bevara radbrytningar

---

## Epic 06 — Execution & Job Lifecycle

**Mål:** Jobb får id, spårbarhet och konsekvent körning.

### Story 06.1 — Job id + job directory

**AC**

* Varje körning får `job_id`
* Upload sparas i `data_dir/jobs/{job_id}/`

### Story 06.2 — Structured logging per job

**AC**

* Logga: job_id, tool_id, filename, ext, duration_ms, status

### Story 06.3 — Error handling wrapper

**AC**

* Exceptions fångas
* UI visar “fel + åtgärdsförslag”
* Stacktrace loggas men visas inte i UI

---

## Epic 07 — Output Artifacts & Downloads

**Mål:** Tools kan generera filer som användare laddar ner.

### Story 07.1 — ToolResult supports files

**AC**

* Tool kan returnera `output_files`
* Fil sparas i job_dir och registreras

### Story 07.2 — Download endpoint for job files

**AC**

* `/jobs/{job_id}/files/{filename}` returnerar fil
* Förhindra path traversal (endast fil i job_dir)

### Story 07.3 — Result partial lists downloads

**AC**

* Om output_files finns: lista med download-länkar

---

## Epic 08 — UI Consistency & Componentization

**Mål:** Standardiserad UX, låg variation mellan tools.

### Story 08.1 — Standard tool page layout

**AC**

* Alla tool-sidor använder samma template
* Endast name/description/accept påverkar UI

### Story 08.2 — Reusable partials

**AC**

* Partial: result state (success/error), empty state, downloads list

### Story 08.3 — Simple UX copy rules

**AC**

* Kort, konsekvent språk
* Felmeddelanden utan tekniska termer som standard

---

## Epic 09 — Governance, Safety & Compliance

**Mål:** Bidrag kan granskas, risker minimeras.

### Story 09.1 — Tool allowlist policy

**AC**

* Dokumenterad policy för accept och begränsningar
* Tool får inte göra nätverksanrop (om ni vill: policy nu, enforcement senare)

### Story 09.2 — Retention policy for job dirs

**AC**

* Konfigurerbar `RETENTION_DAYS`
* Enkel städ-jobb (cron/management command)

### Story 09.3 — PII guidance

**AC**

* Dokumentation: vad som får loggas och inte loggas
* Default: logga metadata, inte innehåll

---

## Epic 10 — Observability & Operations

**Mål:** Driftsättning och felsökning är kontrollerad.

### Story 10.1 — Health endpoint

**AC**

* `/healthz` returnerar “ok”
* Visar även build/version (om ni vill)

### Story 10.2 — Request correlation basics

**AC**

* Job-id i alla relevanta loggrader
* Tydlig start/stop log vid körning

### Story 10.3 — Ops runbook

**AC**

* `docs/runbooks/operations.md` med:

  * konfig
  * backup/restore av data_dir
  * retention och städning
  * incident-felsökning

---

# F. Tool Contract — Design spec v0.1

Det här är centralt för att “grunden” ska bli stabil.

## F1. `tool.yaml` v0.1 (förslag)

```yaml
id: example_summarize
name: Sammanfatta text
description: Extraherar text från dokument och visar förhandsvisning.
entrypoint: hub.tools.example_summarize.tool:run

accept:
  - .pdf
  - .docx
  - .md
  - .py
  - .csv
  - .xlsx

limits:
  max_upload_mb: 25
  timeout_seconds: 10
outputs:
  - type: html
  - type: files
```

## F2. Runtime interface v0.1

* `ing`: normaliserad ingest (text + metadata)
* `params`: dictionary från formfält (t.ex. prompt)
* `job_dir`: katalog där tool får skriva outputfiler

**Konsekvens:** Ni kan senare byta exekveringsmodell (sync → async) utan att ändra tool-syntax.

---

# G. Milestones och leveransplan

## v0.1 “Runnable Foundation”

Innehåll:

* Epic 01–06 (utan downloads)
* Minimal UI + ingest + sync execution
* Basloggning och felhantering

## v0.2 “Artifacts & Retention”

Innehåll:

* Epic 07 + 09.2
* Nedladdningar + retention

## v0.3 “Operational Hardening”

Innehåll:

* Epic 10
* Health endpoints, runbooks, förbättrad loggning
* Valfri enkel auth via reverse proxy (om miljön kräver)

## v1.0 “Governed Platform”

Innehåll:

* Governance-krav som ni faktiskt behöver (policy + enforcement)
* Stabil tool authoring guide
* Testtäckning på ingest + registry + downloads

---

# H. Riskregister och kontroller

| Risk                             | Påverkan             | Kontroll                                         |
| -------------------------------- | -------------------- | ------------------------------------------------ |
| Skannade PDF utan text           | Användare får “tomt” | Tydlig varning + rekommendation (OCR senare)     |
| Långkörande tools                | Timeout/häng         | Timeout limit + förbered ADR för async           |
| Outputfil med traversal          | Security             | Strict filename allowlist + job_dir enforcement  |
| Oavsiktlig PII i logg            | Compliance           | Log policy + strukturerad loggning utan innehåll |
| Tools med osäkra imports/nätverk | Governance           | Code review + policy; enforcement senare         |

---

# I. Rekommenderad “grund” att besluta direkt (utan att bygga fel)

Om ni vill göra “noggranna övervägningar” från start är detta den korta listan av beslut som minimerar omtag:

1. **Kontrakt först:** Lås `tool.yaml` v0.1 + runtime interface innan ni skriver många tools.
2. **Job-dir är sanningen:** Allt (upload, outputs, logs) refererar till job-id.
3. **Allowlist + limits är default:** Filtyper och storlek kontrolleras alltid per tool.
4. **Fel i UI, detaljer i logg:** Separera användarfeedback från teknisk felsökning.
5. **Förbered async utan att implementera:** Gör interface kompatibelt redan nu.

---
