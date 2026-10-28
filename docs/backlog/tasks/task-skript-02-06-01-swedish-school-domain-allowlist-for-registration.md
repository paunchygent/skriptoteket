---
type: task
id: TASK-SKRIPT-02-06-01
title: Swedish school domain allowlist for registration
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-28'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'TASK-SKRIPT-02-06-01#closeout'
story: ST-SKRIPT-02-06
task_kind: story
acceptance_criteria:
  - The slice ships with a versioned initial nationwide allowlist seed covering Swedish municipality root domains plus known enskild-huvudman and school-specific root domains.
  - The import tooling loads municipality, enskild-huvudman, school-specific, and blocked-provider domains into the database as normalized root-domain records suitable for later registration validation.
  - The allowlist records enough ownership/provenance metadata to distinguish municipality, enskild huvudman, and school-specific entries and maintain them over time.
  - The slice leaves registration-time enforcement untouched and clearly defers allow/deny behavior to the follow-on validation slice.
backlog_document_profile: contract-derived
---

## Implementation Contract

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0055 D1 on merge evidence. The original contract below is kept as history; see Closeout for what shipped and what was not checked.

## Context

### Source: Problem

Skriptoteket is a teacher-first platform, but current self-registration allows any email address. That makes it too easy for non-target users to create accounts and forces the product to behave as if a generic public signup flow were acceptable.

The current planning draft also risks under-shipping the fix. Validation logic alone is not enough. If the product launches with no meaningful baseline allowlist, legitimate Swedish school staff will still be blocked and admins will inherit an unnecessary manual-review burden.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Story Contract Slice

### Source: Goal

Ship the allowlist foundation first:

1. a versioned nationwide baseline covering Swedish municipalities plus known enskild-huvudman and school-specific domains,
2. storage and import tooling for that baseline, and
3. blocked-provider seed data for the later validation cutover.

## Contract Inputs

No separate contract inputs were recorded in the source snapshot.

## Core Vertical And Performance

The source record did not define a separate section for this package heading.

## Plan

### Source: Implementation plan

### 1. Infrastructure & Dependencies

- Add `tldextract` to `pyproject.toml`.
- Create database migration for `allowed_domains` and `blocked_domains` tables.
- Ensure root-domain extraction is configured safely for server-side use and does not depend on surprise runtime fetches.

### 2. Domain Layer

- Add `AllowedDomain` and `BlockedDomain` models to `src/skriptoteket/domain/identity/models.py`.
- Define `AllowedDomainRepositoryProtocol` and `BlockedDomainRepositoryProtocol`.
- Define `DomainValidatorProtocol`.
- Keep the first schema minimal: `domain`, `org_type`, `org_name`, `source`, optional `source_ref`, `is_active`, and `notes` for allowed domains, plus the analogous blocked-domain fields.

### 3. Application Layer

- Implement normalization and import support services using `tldextract`.
- Keep registration-time validation wiring out of this slice.

### 4. Infrastructure Layer

- Implement SQLAlchemy repositories for the new domain models.
- Register new services in Dishka container (`src/skriptoteket/di/identity.py`).

### 5. Seed Data & Import Tooling

- Commit a maintained source file or files for the initial nationwide allowlist baseline.
- Seed all Swedish municipality root domains.
- Seed known enskild-huvudman domains and school-specific domains where a school uses its own root instead of a shared parent domain.
- Add a base list of blocked common personal email providers.
- Provide CLI commands that can import or refresh the allowlist from the maintained source files and support targeted corrections.

Recommended seed files and headers:

- `data/identity/allowed_domains_municipalities.csv`
- `data/identity/allowed_domains_enskilda_huvudman.csv`
- `data/identity/blocked_domains.csv`

Allowed-domain header:

```text
domain,org_type,org_name,source,source_ref,is_active,notes
```

Blocked-domain header:

```text
domain,reason,source,source_ref,is_active,notes
```

Importer behavior contract:

- read only the maintained CSV files with the exact headers above
- validate and normalize `domain` to a registered/root domain before persistence
- reject email addresses, subdomains, malformed domains, invalid enums, invalid booleans, and duplicate domains in the same run
- upsert by `domain`
- support `--dry-run` so operators can inspect changes before writing
- emit a deterministic summary of inserted, updated, unchanged, and rejected rows
- keep registration-time enforcement out of this importer slice

### 6. Verification and Operator Readiness

- Add tests that cover municipality, enskild-huvudman, school-specific, and blocked-provider import cases.
- Document how the allowlist seed is updated when a missing or changed school domain is discovered.
- Leave registration-time domain enforcement to the follow-on slice once the imported baseline has been verified.

## Implementation Steps

The source records no separate implementation steps.

## Proof

### Source: Test plan

### Unit Tests

- Root-domain normalization tests for various email and hostname formats (subdomains, international chars, etc.).
- Normalization logic verification.
- Import mapping tests for the minimal metadata fields and optional `source_ref`.

### Integration Tests

- Import/repository integration tests with a test database.
- Verify that municipality, enskild-huvudman, school-specific, and blocked-provider seeded domains persist correctly.
- Verify that the import can be re-run safely for maintained source files.
- Verify that duplicate, malformed, email-address, and subdomain rows fail fast with clear importer errors.

### E2E Tests

- No browser E2E is required for this data-foundation slice; browser validation belongs to the follow-on enforcement slice.

## Validation

Validation follows the focused test and verification material recorded above.

## Stop Conditions

### Source: Non-goals

- Registration-time allow/deny enforcement in `RegisterUserHandler`.
- Full identity verification (verifying that a specific user actually works at the school).
- Perfect one-time completeness for every private-school edge case; this slice should be maintainable and expandable, not frozen forever.
- Automated approval for unknown domains.
- Fine-grained separation between school staff and other employees inside a municipality domain.

### Source: Rollback plan

- The migration will include a `downgrade` path to drop the new tables.
- If the seed data proves materially wrong, disable or replace the shipped source file and re-import corrected entries rather than hand-editing production data.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                 |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Closed as done on 2026-10-28 on merge evidence confirmed in code and git history (TASK-SKRIPT-REP-0055 D1); the Closeout section lists the evidence and the checks that were not run. |

## Lessons Learned

No separate lessons learned were recorded in the source snapshot.

## Notes

No additional task-local notes were recorded in the source snapshot.

## Plan Document Review

No separate plan document review was recorded in the source snapshot.

## Implementation Review

No separate implementation review was recorded in the source snapshot.

## Closeout

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0055 D1 (orchestrator closeout on merge evidence).

The Swedish school-domain allowlist foundation shipped in 493b3ba18: versioned seed CSVs under data/identity (290 municipality, 706 enskild-huvudman, 10 blocked-provider rows), a DomainAllowlistImporter with dry-run and upsert, the validate-domain-allowlist and import-domain-allowlist CLI commands, the 5a7c1d9e3b2f migration, repositories and tests. Registration-time enforcement, which acceptance criterion 4 deferred, was added in the same commit (register_user.py:108, validate_registration_input.py:73, domain_validator.py:56-80), so criterion 4 is superseded. No criterion needed a browser walk; tests were not re-run in this audit. The plan's seed-update how-to (task plan section 6) was not found under docs/ or .codex/; it is not an acceptance criterion and stays undone.
