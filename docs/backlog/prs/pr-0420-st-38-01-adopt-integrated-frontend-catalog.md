---
type: pr
id: PR-0420
title: "ST-38-01 Adopt the integrated frontend catalog"
status: blocked
owners: "agents"
created: 2026-07-31
updated: 2026-07-31
stories: ["ST-38-01"]
dependencies: ["PR-0419"]
tags: ["repository-governance", "frontend"]
acceptance_criteria:
  - "The root facts declare the accepted frontend workspace and the central PNPM, catalog, and design-resource cohort."
  - "Product dependencies and the consumer lockfile remain repository-owned, with a bounded accepted lockfile diff and frontend typecheck, Vitest, and build proof."
---

## Problem

The frontend already pins PNPM 10.26.1 but remains outside the central
catalog/resource cohort.

## Admission gate

This PR remains `blocked` until `TASK-SKR-REP-0004` closes every row below from
the post-PR-0419 checkout. A value that is not present in an accepted central
or consumer authority remains open; implementation must not choose it.

| ID | Required closure before readiness | Stop condition |
| --- | --- | --- |
| F420-01 | Freeze the exact frontend workspace root and manifest set, including the workspace YAML, package-manager manifest, every dependency manifest, the consumer resource destination manifest/package, and their pre-adoption byte hashes. The current checkout observes `frontend/pnpm-workspace.yaml`, `frontend/package.json`, and `frontend/apps/skriptoteket/package.json`; the task ledger must seal or correct that set after PR-0419. | Any unlisted manifest, resource destination, or workspace path is discovered, or the sealed paths/hashes are absent. |
| F420-02 | Verify the central producer identity and cohort: immutable `repository-governance` 0.9.2 at accepted revision `1a8d997477dd06449b00af757ac9df8577f8e16b`; PNPM `10.26.1`; the exact 17-entry catalog from the central IFC-001..006 authority and its source identity/digest; and `resources/frontend-design-system/huleedu-integrated/` package/manifest version `0.1.7`, schema, package identity, complete export set, and every manifest-owned SHA-256 digest. | A catalog/resource version, source identity, or digest is supplied only by local inference, or the catalog and resource authorities disagree. |
| F420-03 | Record ownership and the permitted tracked-file write set. Skriptoteket owns product dependency manifests and `frontend/pnpm-lock.yaml`; central tooling may publish only its reserved catalog block and may not rewrite consumer-owned bytes. The task ledger must name each consumer manifest/resource file and the exact owned regions. | A central operation edits product dependencies or the consumer lockfile outside the sealed task write set, or a file/region has no owner. |
| F420-04 | Seal a bounded consumer-lock diff before readiness: baseline and post-adoption hashes for `frontend/pnpm-lock.yaml`, every changed importer/package snapshot, each old/new resolution, and the accepted catalog/resource reason. Only the sealed dependency-closure diff may land; unrelated product dependency or transitive churn is out of scope. | The lock diff is not enumerated and bounded, or any hunk falls outside the accepted dependency closure. |
| F420-05 | Freeze the required frontend proof and its exact selectors/artifact locations: central catalog synchronization plus read-only catalog validation, resource-manifest/digest validation, `npm exec --yes --package=pnpm@10.26.1 -- pnpm install --frozen-lockfile` at the sealed workspace, `pdm run fe-type-check`, focused Vitest, and `pdm run fe-build`, followed by docs validation and diff hygiene. | A proof command, focused selector, workspace, manifest, digest, or result artifact is missing, broad, or not tied to the sealed ledger. |
| F420-06 | Freeze rollback ownership and bytes: restore the pre-adoption workspace catalog block, consumer manifests, resource files/manifests, and lockfile atomically from the sealed hashes; leave central package/resource authorities unchanged; and report any non-rollbackable PNPM store/cache state separately. | Rollback would touch an unowned product file, leave a partial tracked-file state, or require an alias, compatibility surface, or fail-open path. |

These rows are admission facts, not implementation authority. Until they are
closed and independently reviewed, this envelope authorizes no consumer
manifest, resource, or lockfile mutation.

## Implementation plan

After the admission ledger is sealed, adopt the accepted shared catalog and
resource manifest without changing product dependency ownership. Synchronize
only the reserved workspace block, apply the explicitly owned consumer
manifest/resource changes, and record the bounded lock diff. Prove frozen
synchronization, exact resource digests, typecheck, focused Vitest, and shipped
build.

## Test plan

Run the sealed catalog/resource validators and frozen PNPM synchronization,
then `pdm run fe-type-check`, the task-ledger focused `pdm run fe-test` selector,
and `pdm run fe-build`. Confirm the bounded lock diff and owned-file hashes,
then run `pdm run docs-validate` and `git diff --check`.

## Rollback plan

Restore only the sealed task-owned workspace catalog block, consumer manifests,
resource files/manifests, and lock bytes atomically. Preserve product-owned
bytes outside the write set and leave central package/resource authorities
unchanged; if PNPM validation or frontend proof fails, stop and use governed
forward repair rather than adding a compatibility or fallback surface.
