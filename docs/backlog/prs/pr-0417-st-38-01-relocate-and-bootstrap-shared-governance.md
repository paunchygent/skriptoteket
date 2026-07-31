---
type: pr
id: PR-0417
title: "ST-38-01 Relocate and bootstrap shared governance"
status: blocked
owners: "agents"
created: 2026-07-31
updated: 2026-07-31
stories:
  - "ST-38-01"
tags: ["repository-governance", "bootstrap", "relocation"]
acceptance_criteria:
  - "The clean checkout moves to /Users/olofs_mba/Documents/Repos/Skriptoteket without changing Git history or remote-main equality."
  - "The relocated consumer pins repository-governance 0.9.2 through the immutable dependency URL ending in @1a8d997477dd06449b00af757ac9df8577f8e16b#subdirectory=packages/repository_governance; its lock entry records version 0.9.2 with ref and revision both equal to 1a8d997477dd06449b00af757ac9df8577f8e16b, and the installed semantic-identity probe passes."
  - "The sole facts home is root pyproject.toml with schema-version = 3, repository = \"skriptoteket\", owners.service = [\"skriptoteket\"], and one root setup project whose groups are exactly [\"default\", \"monorepo-tools\"]."
  - "The package synchronizer generates its complete reserved routine block (setup, new-worktree, format, lint, typecheck, test, check, new-doc, new-epic, new-story, new-task, new-review, docs-sync, docs-validate, format-md, check-md, format-md-all, check-md-all) plus auxiliary run-hemma and staleness-audit bindings; no hand-written alias or second facts home is introduced."
  - "Public setup and new-worktree prove a clean usable TASK-SKR-REP-0002 worktree from the relocated checkout, after which normal worktree admission resumes and the one-time direct-main exception expires."
  - "The bootstrap does not migrate the governed corpus, adopt quality/frontend facts, or alter legacy lifecycle fields; those fields remain unchanged until PR-0418 owns their migration."
---

## Problem

The shared creator cannot admit a task worktree before Skriptoteket has the
package pin and minimal repository facts that the creator validates.

## Authority and scope

ST-SKILL-08-06 is the central authority for this consumer slice. Its closed
SKR-004G, SKR-004H, SKR-004I, and SKR-004N decisions authorize one serialized
direct-`main` bootstrap only. The plan-document-reviewer finding for the
central story requires these exact task-level facts before this PR can become
ready; this record closes them without changing the story's lifecycle or
claiming implementation proof.

The implementation write set at the relocated consumer root is exactly:

- `pyproject.toml`: the immutable `monorepo-tools` dependency, the sole
  schema-v3 facts tables, and the package-owned marked binding block.
- `pdm.lock`: the generated package entry and dependency closure for version
  `0.9.2`, with `ref` and `revision` equal to the immutable 40-character
  revision.
- `tests/test_repository_governance_bootstrap.py`: focused consumer contract
  assertions for dependency/lock identity, facts, generated bindings, and the
  red/green admission boundary.

No other tracked consumer file may change in this slice. In particular, no
governed-corpus source, backlog lifecycle field, quality/frontend table,
nonreserved product command, local wrapper, alias, fallback, or compatibility
surface is within the write set. Existing declarations whose names are in the
package-owned reserved set are replaced only by the marked generated block;
all other product-owned declarations remain byte-for-byte unchanged.

## Decision And Assumption Ledger

| ID | Type | Status | Question/Assumption | Other plausible options | Motivation | Recommendation/Decision | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P417-01 | baseline | closed | Which Git state is the admission basis? | Start from a local divergent or dirty checkout. | The central story names clean remote `main` as the only reproducible baseline. | Freeze remote `main` `721f45396b1eb7db90911b16c5ec78656919121d`, prove equality and cleanliness, and stop on any drift. | ST-SKILL-08-06 SKR-001; reviewer-approved baseline |
| P417-02 | relocation | closed | Where must the sole clean checkout live before tracked edits? | Keep the CascadeProjects path or edit before relocation. | Central paths and later worktree siblings must resolve from the approved consumer root. | Move the checkout to `/Users/olofs_mba/Documents/Repos/Skriptoteket` before editing tracked files; prove Git root, branch, upstream, HEAD, and no linked worktrees. | ST-SKILL-08-06 SKR-004G/H; user closure |
| P417-03 | dependency | closed | Which producer identity unlocks the walking skeleton? | Use a tag-only dependency, mutable branch, source checkout, or intermediate release. | Package 0.9.2 is the reviewed immutable producer; tag-shaped or mutable references can pass synchronization while failing semantic identity. | Pin `repository-governance @ git+https://github.com/paunchygent/skill-repository.git@1a8d997477dd06449b00af757ac9df8577f8e16b#subdirectory=packages/repository_governance`; require installed version `0.9.2`, lock `ref` equal to that revision, lock `revision` equal to that revision, and a green semantic-identity probe. | ST-SKILL-08-06 SKR-004I; ST-SKILL-08-05 closeout; reviewer finding |
| P417-04 | facts | closed | What is the smallest package-valid facts home? | Keep a YAML home, use schema v1, add quality/frontend tables, or create a second TOML home. | Package 0.9.2 requires schema v3 while setup admission needs only identity, typed ownership, and root synchronization. | In root `pyproject.toml`, add exactly schema-version `3`, repository `skriptoteket`, owners service `skriptoteket`, and one setup project `{ path = ".", groups = ["default", "monorepo-tools"] }`; add no quality, frontend, Hemma, or YAML facts. | ST-SKILL-08-06 SKR-004I; package `load_setup_facts`; reviewer finding |
| P417-05 | bindings | closed | Which generated bindings belong in this slice? | Add only setup/new-worktree manually, keep consumer aliases, or defer the package block. | The package synchronizer owns one complete marked block; partial or bypassed bindings drift and prevent deterministic proof. | Generate the complete routine set `setup`, `new-worktree`, `format`, `lint`, `typecheck`, `test`, `check`, `new-doc`, `new-epic`, `new-story`, `new-task`, `new-review`, `docs-sync`, `docs-validate`, `format-md`, `check-md`, `format-md-all`, `check-md-all`, plus auxiliary `run-hemma` and `staleness-audit`; reserved-name declarations are replaced only inside that block, nonreserved product commands remain unchanged, and this slice proves only setup/new-worktree. | Central `ROUTINE_BINDINGS`/`AUXILIARY_BINDINGS`; ST-SKILL-08-06 SKR-004I |
| P417-06 | write-set | closed | Which tracked consumer files may the bootstrap mutate? | Touch current docs, product commands, lock-adjacent files, or migration inputs. | A bounded write set prevents the admission repair from becoming corpus or product work. | Permit only root `pyproject.toml`, root `pdm.lock`, and the focused `tests/test_repository_governance_bootstrap.py`; generated bindings remain inside `pyproject.toml`. | Reviewer finding 2; ST-SKILL-08-06 decomposition |
| P417-07 | lifecycle | closed | Which existing lifecycle fields and records remain outside this slice? | Normalize PR/story statuses or migrate legacy records while bootstrapping. | PR-0418 owns current-corpus migration and historical lifecycle disposition. | Leave all legacy lifecycle fields and governed-corpus records unchanged until PR-0418; this PR only records the bootstrap contract and its proof boundary. | ST-SKILL-08-06 SKR-004P; PR-0418 dependency |
| P417-08 | proof | closed | What proves the minimal slice is complete? | Rely on lock/install success alone or run an unscoped repository suite. | Lock synchronization does not establish semantic identity, facts validity, binding ownership, or usable worktree admission. | Retain red missing-facts setup/worktree failures; green-proof exact dependency/lock/installed identity, schema-v3 facts, complete binding drift check, `pdm run setup`, `pdm run new-worktree TASK-SKR-REP-0002`, clean worktree usability, docs validation, and diff check. | Reviewer finding 2; ST-SKILL-08-06 live verification plan |
| P417-09 | sequencing | closed | When does the direct-main exception expire? | Continue direct-main edits for PR-0418 or later slices. | Normal admission is the safety boundary once the first skeleton passes. | Serialize this bootstrap on clean `main`; after the green worktree proof, all later work enters through normal governed `new-worktree` admission. | ST-SKILL-08-06 SKR-004N; user approval |

## Goal

Establish the smallest installed-package consumer boundary that makes every
later slice governable through normal worktrees.

## Non-goals

- Corpus mutation, quality topology, frontend adoption, or retirement.
- Product, deployment, database, or Hemma changes.

## Implementation plan

1. Reconfirm clean remote-main equality and the single-worktree inventory.
2. Move the checkout directory and prove Git root, branch, upstream, remote,
   HEAD, and cleanliness at the destination.
3. In the destination root, pin the exact 0.9.2 dependency and regenerate only
   the matching `pdm.lock` package entry; prove version, `ref`, `revision`, and
   installed semantic identity all match `1a8d997477dd06449b00af757ac9df8577f8e16b`.
4. Add the sole schema-v3 facts home and exact root setup project in
   `pyproject.toml`; do not add quality, frontend, Hemma, YAML, or another
   facts home.
5. Synchronize the complete package-owned routine and auxiliary binding blocks
   atomically; assert their exact names and commands in the focused consumer
   contract test while preserving every nonreserved product-owned PDM
   declaration.
6. Run the public red/green proof from the relocated root: first retain the
   missing-facts failures for `pdm run setup` and
   `pdm run new-worktree TASK-SKR-REP-0002`, then run `pdm run setup` and create
   one disposable governed worktree with the same task ID. Prove the result is
   clean and usable, remove only that disposable proof worktree, and resume
   normal admission for later slices.

## Test plan

- `tests/test_repository_governance_bootstrap.py` is the focused contract
  surface. It asserts the dependency URL, installed version, lock version/ref/
  revision, semantic identity, schema-v3 repository/owner/setup values, sole
  facts home, complete generated binding names, preservation of product-owned
  nonreserved PDM declarations, and absence of quality/frontend tables.
- Behavioral red/green retains missing-facts failures, then proves the exact
  same public invocations succeed after bootstrap:

  ```text
  pdm run setup
  pdm run new-worktree TASK-SKR-REP-0002
  ```

  The green result must identify a clean usable task worktree created by the
  installed package without a package source checkout.
- `pdm run setup`
- `pdm run new-worktree TASK-SKR-REP-0002` in the disposable admission proof.
- Focused package/consumer adoption tests, `pdm run docs-validate`, and
  `git diff --check`.

## Rollback plan

Before the first commit, move the unchanged clean checkout back only if
destination proof fails. After tracked bootstrap integration, use normal
merge-only forward repair; do not reset or create compatibility surfaces.

## Stop conditions

- Source or destination is dirty, divergent, already occupied, or has linked
  worktrees.
- The exact 0.9.2 producer is unavailable.
- The dependency or lock does not prove version `0.9.2` and both `ref` and
  `revision` equal to `1a8d997477dd06449b00af757ac9df8577f8e16b`.
- Schema version, repository, typed service owner, root setup groups, or the
  complete generated binding set differs from this record.
- The focused contract test, semantic-identity probe, or either public
  setup/worktree invocation fails.
- Bootstrap needs quality, frontend, corpus, or product behavior.
- Public worktree admission needs a raw Git workaround.

## Proof boundary

This PR proves the walking skeleton only: immutable package identity, one
schema-v3 facts home, complete generated binding ownership, frozen setup, and
one clean governed worktree. PR-0418 owns current-corpus migration and all
legacy lifecycle disposition; PR-0419 owns topology-derived quality. No later
slice may use this bootstrap exception or treat its generated bindings as
quality/frontend adoption proof.
