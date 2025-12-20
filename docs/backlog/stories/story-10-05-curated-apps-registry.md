---
type: story
id: ST-10-05
title: "Curated apps registry and catalog integration"
status: done
owners: "agents"
created: 2025-12-19
epic: "EPIC-10"
acceptance_criteria:
  - "Given curated apps are defined in the registry, when a user opens Katalog, then curated apps are visible alongside tools (role-gated)"
  - "Given a curated app is visible, when a user opens it, then the app presents platform-rendered outputs/actions and can be executed"
  - "Given a curated app exists, when an admin/contributor uses the tool editor, then curated apps are not editable via that workflow"
dependencies: ["ADR-0023"]
---

## Context

Curated apps allow the owner to ship richer “apps” safely without exposing those capabilities to user-authored scripts
or the editor workflow.
