---
type: story
id: ST-05-04
title: "Suggestion template migration"
status: done
owners: "agents"
created: 2025-12-15
epic: "EPIC-05"
acceptance_criteria:
  - "Given the suggestion form loads, when viewing checkboxes, then they display as flex-wrap items"
  - "Given the review queue loads, when viewing a suggestion, then appropriate status dot color is visible"
---

## Context

Migrating the suggestion submission and review workflows to the new design system.

## Tasks

- Convert `suggestions_new.html` to use HuleEdu form styling
- Replace `<br>` checkbox layout with flex checkbox groups
- Convert `suggestions_review_queue.html` with status dots
- Convert `suggestions_review_detail.html` with labels, form groups, decision history styling
