---
type: story
id: ST-38-01
title: "Adopt the shared governed development system"
status: blocked
owners: "agents"
created: 2026-07-31
updated: 2026-07-31
epic: "EPIC-38"
acceptance_criteria:
  - "Given clean remote main, when the bootstrap completes, then immutable 0.9.2 setup and governed worktree admission pass from the relocated checkout."
  - "Given the approved corpus manifest, when migration completes, then every current authoritative governed document uses the common contract and every terminal backlog record remains historical."
  - "Given routine and frontend adoption, when final cutover runs, then named scopes, product preservation, read-only Hemma transport, staleness, handoff, and exact retirement pass without an unscoped aggregate."
---

## Context

This repository-owned story implements Skill Repository `ST-SKILL-08-06`
without redefining its accepted cross-repository decisions.

## Slice Sequence

1. `PR-0417`: relocation and minimal package/facts walking skeleton.
2. `PR-0418`: complete governed-corpus migration and validator cutover.
3. `PR-0419`: complete bindings and topology-derived quality.
4. `PR-0420`: integrated frontend catalog/resources.
5. `PR-0421`: serial operational retirement and story proof.

## Notes

The current EPIC/ST/PR records are bootstrap authority. PR-0418 migrates their
nonterminal meaning to `TASK-SKR-REP-0001` through `0005` under the common
contract. Only PR-0417 may use the approved serialized direct-`main` exception;
later slices require governed worktrees.
