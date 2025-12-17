---
type: prd
id: PRD-script-hub-v0.2
title: "Script Hub PRD v0.2 Features (Planned)"
status: draft
owners: "agents"
created: 2025-12-17
product: "script-hub"
version: "0.2"
---

## Summary

This document outlines key features planned for the post-MVP (v0.2) release of the Script Hub. The primary focus is enhancing tool capability through statefulness and expanding the governance model.

## Feature: User-Specific Tool Memory

### Context & Problem
Currently, tools are **stateless**. Every execution is an isolated event. This prevents tools from:
1.  Remembering past actions (e.g., "Skip rows I processed yesterday").
2.  Learning user preferences (e.g., "Default to 'Class 9B' for this user").
3.  Providing incremental processing (e.g., "Compare this upload to the last one").

### Solution
Implement a **small, persistent, user-specific JSON store** (< 50KB) for each tool.

### Technical Requirements
1.  **Storage**: New table `tool_user_state` (`user_id`, `tool_id`, `state_data` JSONB).
2.  **Injection**: The runner injects the previous state into the container (e.g., as `memory.json`).
3.  **Extraction**: The runner extracts the updated state after execution and updates the database.
4.  **Contract**:
    *   **Env Var**: `SKRIPTOTEKET_MEMORY_PATH` points to the read/write JSON file.
    *   **Concurrency**: User-scoped locking or "Last Write Wins" policy (acceptable for v0.2).
5.  **Controls**: Users must have a "Clear Memory" option in the "My Tools" interface to reset a tool's state.

### User Story
> "As a Special Educator, I want the 'Attendance Analyzer' to remember which students I flagged last week, so I don't have to manually filter them out of this week's report."

## Feature: Interactive Execution (Artifact-Driven UI)

### Context & Problem
Currently, script execution is **linear**: Input -> Processing -> Final Output.
Complex tasks often require a **human-in-the-loop** to verify or organize data (e.g., grouping students into breakout sessions) before finalizing the result. Doing this strictly via file re-uploads is tedious.

### Solution
Allow scripts to request a **Rich UI** (specifically a "Slot-ID Grid") by returning a standardized data artifact. The platform renders this UI, allowing the user to manipulate the data visually and save the result back to the tool's memory.

### Technical Requirements
1.  **Dependencies**: Requires **User-Specific Tool Memory** (above) to persist the user's interactive choices.
2.  **Protocol (Script Output)**:
    *   Scripts can output a reserved artifact file: `ui_schema.json`.
    *   Example Content: `{"ui_type": "slot_grid_v1", "data": {...}}`.
    *   If present, the frontend **replaces** the standard HTML result view with the specified UI Component (e.g., the Slot-ID Grid).
3.  **Frontend (Web App)**:
    *   Detects `ui_schema.json`.
    *   Initializes the specific JavaScript GUI library (e.g., for the Slot Grid).
    *   Passes the JSON data to the library.
4.  **Feedback Loop (Persistence)**:
    *   **Endpoint**: `POST /api/tools/{tool_id}/memory`.
    *   **Action**: Receives the modified state from the UI and directly saves it to the `tool_user_state` table.
    *   **Next Run**: The next time the script runs, it reads this saved state to pre-populate the grid (e.g., "Student A was in Group 1 last time").

### User Story
> "As a Teacher creating seating charts, I want to upload my class list and see a drag-and-drop grid. The system should remember where I placed specific students last time so I only have to assign the new transfer student."

## Feature: Advanced Input Handling (Multi-File & External Sources)

### Context & Problem
The v0.1 runner restricts inputs to a **single file**.
Real-world tasks often require correlating data from multiple sources (e.g., "Compare *this month's* schedule with *last month's* absence list") or fetching data from external systems (e.g., LMS, HR system) rather than requiring the user to manually download and re-upload files.

### Solution
Expand the execution model to support **Multiple Inputs**.
"Inputs" can be direct file uploads or references to external data sources that the platform fetches and bundles before execution.

### Technical Requirements
1.  **Frontend**:
    *   Upgrade the upload form to support multiple files (e.g., specific slots like "Source A", "Source B" or a generic "Add File" list).
    *   (Future) Add "Import from..." buttons that fetch data on the client-side or trigger backend fetchers.
2.  **Protocol (Command)**:
    *   Update `RunActiveToolCommand` to accept `inputs: List[InputArtifact]` instead of single `input_bytes`.
3.  **Runner**:
    *   **Container Layout**: Map all inputs into the `/work/input/` directory.
    *   **Env Var**: Provide `SKRIPTOTEKET_INPUT_MANIFEST` (JSON) listing available files and their metadata (source, original name).
4.  **Script Contract**:
    *   Scripts must be able to handle iterating through `/work/input/` or looking for specific filenames.
    *   (Backward Compatibility): If only one file is uploaded, `SKRIPTOTEKET_INPUT_PATH` still points to it.

### User Story
> "As an Administrator, I want to upload the 'Budget Report' and the 'Staff List' simultaneously so the script can calculate the cost per department without me having to merge the Excel files manually first."

## Feature: Native PDF Output Support

### Context & Problem
Scripts generate HTML for immediate viewing. However, many administrative workflows (signing, archiving, emailing) require **PDF documents**.
Currently, users must use their browser's "Print to PDF" function, which often breaks formatting and lacks professional polish (headers, footers, page breaks).

### Solution
Equip the runner environment with a high-fidelity HTML-to-PDF engine (e.g., WeasyPrint) and provide a simple API for scripts to generate PDF artifacts.

### Technical Requirements
1.  **Runner Environment**:
    *   Pre-install `WeasyPrint` (Python library) in the `skriptoteket-runner` image.
    *   (Note: System dependencies like `libpango` and `libcairo` are already present in the Dockerfile).
2.  **Script Helper**:
    *   Inject a helper module or function (e.g., `save_as_pdf(html_string, filename)`) so script authors don't need complex boilerplate.
3.  **Output**:
    *   Scripts save the generated PDF to `/work/output/`.
    *   The platform automatically picks it up as a downloadable artifact.

### User Story
> "As a Principal, I want the 'Incident Report' tool to produce a properly formatted PDF with the school logo and page numbers, so I can file it immediately without formatting it myself."

## Feature: Personalize Tool Output (Persisted Styles)

### Context & Problem
Different users have different needs for how information is presented.
*   **Accessibility:** Some users need larger fonts or high-contrast themes.
*   **Branding:** Different schools need their specific logos or header colors on reports.
*   **Preference:** Some users prefer "Dense Tables" while others want "Summary Cards".
Currently, scripts are "one size fits all" unless the user manually uploads a settings file every time.

### Solution
Standardize a **"Tool Settings"** interface.
Scripts can declare configurable style options (color, layout, font size). The platform generates a settings form, and the user's choices are automatically **saved to their Tool Memory** and injected into every future run.

### Technical Requirements
1.  **Schema**: Scripts can optionally provide a `settings_schema.json` (defining fields like `theme_color`, `font_size`, `logo_url`).
2.  **UI**: The platform renders a "Settings" (⚙️) panel next to the "Run" button based on the schema.
3.  **Persistence**: Values are stored in the existing `tool_user_state` (User Memory).
4.  **Injection**: Settings are merged into the `memory.json` injected into the runner, so the script can simply read `memory['settings']['theme_color']` to style its HTML/PDF output.

### User Story
> "As a User with low vision, I want to set the 'Font Size' to 'Large' for the 'Weekly Letter' tool and have it remember that preference every time I generate a PDF."

## Feature: Integrated NLP Services (Grammar & Text Analysis)

### Context & Problem
Teachers frequently need to analyze student texts for readability (LIX/word counts) or grammar correctness.
Implementing this in individual scripts is inefficient because:
1.  **Size:** NLP models (spaCy) and tools (LanguageTool) are massive (GBs), making the runner image bloated.
2.  **Complexity:** Script authors shouldn't need to be NLP experts to get basic metrics.
3.  **Performance:** Loading models for every 5-second script run is too slow.

### Solution
Deploy a dedicated **Internal NLP Microservice** (hosting LanguageTool and spaCy models).
Provide a simple Python client (`skriptoteket.nlp`) inside the runner that allows scripts to send text and receive analysis.

### Technical Requirements
1.  **Infrastructure**:
    *   New Container: `nlp-service` (FastAPI wrapper around spaCy + LanguageTool server).
    *   **Network Strategy**: Use a specific **Internal Docker Network** linking only the `runner` and `nlp-service`. This maintains the "No Internet" security policy for scripts while allowing them to reach this specific utility.
2.  **Client Library**:
    *   Inject a helper library `skriptoteket.nlp` into the runner.
    *   Methods: `check_grammar(text, lang="sv")`, `get_metrics(text)`.
3.  **Capabilities**:
    *   **Grammar**: Detect typos, grammar errors (via LanguageTool).
    *   **Metrics**: LIX, word count, sentence length, named entities (via spaCy).

### User Story
> "As a Language Teacher, I want to upload a folder of student essays and get a summary table showing the LIX score and common grammar mistakes for each student, without me having to check them manually."

## Feature: Enhanced Observability (Placeholder)
*To be defined: Better logging and error tracking for tool maintainers.*

## Feature: Interactive Inputs (Placeholder)
*To be defined: Support for text/dropdown inputs in addition to file uploads.*
