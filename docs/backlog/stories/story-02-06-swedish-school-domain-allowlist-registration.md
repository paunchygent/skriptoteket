---
type: story
id: ST-02-06
title: "Swedish school domain allowlist for registration"
status: ready
owners: "agents"
created: 2026-03-29
updated: 2026-03-29
epic: "EPIC-02"
acceptance_criteria:
  - "Given this first slice ships, when the initial allowlist seed is inspected, then it contains a nationwide baseline of active Swedish municipality root domains plus known enskild-huvudman and school-specific root domains used for staff email registration."
  - "Given the baseline is imported into the database, when an admin inspects an allowlist entry, then municipality, enskild huvudman, and school-specific rows can be distinguished clearly enough to maintain the list over time."
  - "Given the import tooling runs on the maintained source files, when municipality and enskild-huvudman data is loaded, then the resulting allowed-domain rows are normalized to registered/root domains suitable for later registration validation."
  - "Given the baseline import slice ships, when the blocked-domain seed is inspected, then common personal-email providers are present as explicit blocked domains for the later enforcement slice."
  - "Given this story is not yet the enforcement cutover, when the slice is reviewed, then registration-time allow/deny behavior is explicitly deferred to a follow-on implementation slice that consumes the imported baseline."
  - "Given the seed files and import path are maintained in the repo, when a missing or changed school domain is discovered, then operators have a documented and versioned way to refresh the allowlist instead of hand-editing production data."
dependencies: ["ST-02-03"]
ui_impact: "No direct end-user UI impact in this slice; operator-facing import/maintenance workflow only."
data_impact: "New tables: allowed_domains, blocked_domains. Migration required."
---

## Context

To keep Skriptoteket teacher-first without requiring manual provisioning for every user, self-registration must eventually be limited to the Swedish school sector. For this slice, though, the priority is to build the baseline dataset and import path first.

That means the first outcome is operational rather than user-facing: Skriptoteket should gain a maintained, nationwide allowlist baseline covering Swedish municipalities plus known enskild-huvudman and school-specific domains. Registration-time enforcement comes immediately after, once the seed/import foundation is trustworthy.

## Implementation notes

### Domain Normalization

- Use `tldextract` to extract the registered/root domain.
- `anna@edu.stockholm.se` -> `stockholm.se`
- `teacher@mail.harryda.se` -> `harryda.se`

### Data Model

- `allowed_domains`: `domain` (PK), `org_type`, `org_name`, `source`, `source_ref`, `is_active`, `notes`.
- `blocked_domains`: `domain` (PK), `reason`, `source`, `source_ref`, `is_active`, `notes`.

Keep the first schema deliberately small. The important first-cut data is:

- the allowed or blocked root domain
- whether the owner is a municipality or enskild huvudman
- the readable organization name
- provenance and optional source reference
- whether the row is currently active
- optional notes for ambiguity or maintenance context

### Validation Logic

This story prepares the data and normalization model for validation, but does not yet switch registration enforcement on.

The follow-on slice should:

1. Normalize email to extract root domain.
2. Check `blocked_domains` (e.g., gmail.com, outlook.com). If matched, reject.
3. Check `allowed_domains`. If matched and `is_active=True`, allow.
4. If no match, reject with a message indicating manual review or contact requirement.

### Seed Data and Provenance

- Commit a versioned initial allowlist seed in the repo so the first deployment is useful immediately.
- Seed all Swedish municipality root domains.
- Seed known enskild-huvudman domains and school-specific domains used by schools where a shared parent root is not sufficient.
- Store provenance per entry through `source` plus optional `source_ref` so future updates can distinguish registry-backed, manually researched, and operator-corrected rows.

### CSV Contract

Maintain three repo-managed CSV files:

- `data/identity/allowed_domains_municipalities.csv`
- `data/identity/allowed_domains_enskilda_huvudman.csv`
- `data/identity/blocked_domains.csv`

Required headers for allowed-domain files:

```text
domain,org_type,org_name,source,source_ref,is_active,notes
```

Required headers for blocked-domain files:

```text
domain,reason,source,source_ref,is_active,notes
```

Header rules:

- Keep headers lowercase and stable.
- `source_ref` may be empty.
- `notes` may be empty.
- `is_active` must be either `true` or `false`.

### Importer Contract

The first importer should be intentionally strict and boring:

- Input is one or more repo-managed CSV files with the exact headers above.
- `domain` must be a registered/root domain, not an email address and not a subdomain.
- The importer must lowercase and trim domains before validation and persistence.
- The importer must reject rows with missing required columns, invalid `org_type`, invalid `is_active`, malformed domains, or duplicate domains inside the same import run.
- The importer must upsert by `domain` so maintained source files can be re-imported safely.
- The importer must persist only normalized root domains to the database.
- The importer must support a dry-run mode that reports inserts, updates, unchanged rows, and rejected rows.
- The importer must produce a deterministic summary suitable for CI logs or operator review.
- The importer must not silently infer extra metadata beyond the CSV contract.

### Admin/CLI

- Command to import or refresh municipality domains from a maintained source file.
- Command to import or refresh enskild-huvudman and school-specific domains from a maintained source file.
- Command to add, disable, or correct individual domains without editing production rows by hand.

### Verification

- Unit tests for normalization utility and import transforms.
- Integration tests for repository and import flows that prove municipality, enskild-huvudman, school-specific, and blocked-provider rows are stored correctly with the expected minimal metadata.
- Verification that the initial source files import into the database and can be refreshed repeatably.
- Verification that malformed rows, duplicate domains, email-address input, and subdomain input are rejected with clear operator-facing errors.
- Registration-time allow/deny tests belong to the follow-on enforcement slice.
