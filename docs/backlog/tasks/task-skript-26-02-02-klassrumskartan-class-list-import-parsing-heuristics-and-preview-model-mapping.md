---
type: task
id: TASK-SKRIPT-26-02-02
title: 'Klassrumskartan: class-list import parsing heuristics and preview model mapping'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-26-02
task_kind: story
acceptance_criteria:
- Given the backend receives extracted text or tabular rows from a document, when
  the heuristic parser runs, then it identifies a suggested class name and extracts
  probable student names using the logic from the established prototype script.
- Given a row contains data that cannot be confidently parsed as a student name (e.g.,
  blank rows, headers, noise), when the parser evaluates it, then the row is categorized
  as an 'ambiguous row' rather than silently dropped or incorrectly coerced into a
  name.
- Given the parser identifies student names, when it builds the result, then it attempts
  to split 'family_name' and 'given_name' if a comma format is used, otherwise falling
  back to a full string.
- Given multiple extraction variants exist (e.g., tabular vs raw text), when the parser
  runs, then it accumulates and deduplicates records intelligently, picking the best
  representation based on the prototype's merge priority.
dependencies:
- ST-SKRIPT-26-02
---

## Context

### Source: Problem

Extracting clean student lists from messy, human-authored files (like Excel sheets, exported CSVs, or text blobs from PDFs) is highly error-prone. We have a proven Python prototype script that handles character normalization, class name inference, and name extraction heuristics, but it needs to be adapted into the strict Domain-Driven Design (DDD) architecture of Skriptoteket.

## Decision And Assumption Ledger

### Source: Locked design decisions

- The parsing logic must be isolated in the `domain` or `application` layer as pure Python, independent of FastAPI or HTTP boundaries.
- The logic from the prototype script will be ported with minimal behavioral changes, but modernized to fit our strict typing, Pydantic models, and error handling.
- The concept of `ExtractionResult` and `StudentRecord` from the prototype will map cleanly to the inputs and outputs of the parser protocol.
- **Critical rule:** The parser must be defensive. If it is not sure a row is a name, it must return it in the `ambiguous_rows` list of the preview model. We rely on the teacher to manually review and correct these in the UI. We do not want to automatically create a student named "Sida 1 av 2".

## Story Contract Slice

### Source: Goal

Adapt the standalone heuristic parsing script into a clean, testable domain service (`ClassListHeuristicParser`) that implements the protocol defined in TASK-SKRIPT-26-02-01 and populates the `ClassListImportPreview` model.

## Contract Inputs

The source does not record separate contract inputs.

## Plan

### Source: Implementation plan

1. Create `src/skriptoteket/domain/curated_apps/classroom_planner/import_heuristics.py`.
2. Port the core logic from the prototype:
   - `normalize_text`, `canonical_name_key`, `collapse_ws`
   - `score_class_candidates_from_text`, `score_class_candidates_from_rows`, `detect_class_name`
   - `parse_text`, `parse_rows`, `extract_candidate_from_text_line`
   - The `StudentAccumulator` and merge priority logic.
3. Adapt the output of the ported logic to construct the `ClassListImportPreview` (or equivalent domain result object) that categorizes rows into `parsed_students` and `ambiguous_rows`.
4. Implement the concrete `ClassListHeuristicParser` and wire it up to the route established in TASK-SKRIPT-26-02-01.

## Implementation Steps

The source does not provide separate implementation steps.

## Proof

### Source: Test plan

- Extensive pure unit tests for `import_heuristics.py`.
- Provide specific string and tabular fixtures that mirror real-world messy data (comma-separated names, names with numbers, headers mixed in) and assert they are categorized correctly into valid names vs. ambiguous rows.
- Ensure the class name scoring accurately picks the best candidate.

## Validation

### Source: Test plan

- Extensive pure unit tests for `import_heuristics.py`.
- Provide specific string and tabular fixtures that mirror real-world messy data (comma-separated names, names with numbers, headers mixed in) and assert they are categorized correctly into valid names vs. ambiguous rows.
- Ensure the class name scoring accurately picks the best candidate.

## Stop Conditions

### Source: Non-goals

- Adding machine learning or LLM-based parsing. The heuristics (regexes, header lists) from the prototype are sufficient.
- Handling file reading from disk. The parser should accept raw strings or list of lists (from the extractors defined in TASK-SKRIPT-26-02-01).

## Lessons Learned

The source does not record separate lessons learned.

## Notes

### Source: Rollback plan

- Revert the heuristic implementation to the dummy empty-list stub.

## Plan Document Review

The source does not include a plan document review record.

## Implementation Review

The source does not include an implementation review record.
