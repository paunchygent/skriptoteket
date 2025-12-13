---
type: story
id: ST-03-02
title: "Admin reviews suggestions (accept/modify/deny)"
status: ready
owners: "agents"
created: 2025-12-13
epic: "EPIC-03"
acceptance_criteria:
  - "Given I am an admin, when I open the review queue, then I can view suggested scripts with metadata and history."
  - "Given a suggestion, when I accept/modify/deny it, then the decision and rationale are recorded."
  - "Given I accept a suggestion, when the decision is saved, then a draft tool entry is created and linked to the suggestion (not runnable/published)."
---
