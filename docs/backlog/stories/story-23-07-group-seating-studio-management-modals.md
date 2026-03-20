---
type: story
id: ST-23-07
title: "Klassrumskartan — Management Modals (Rosters & Rooms)"
status: done
owners: "agents"
created: 2026-03-20
epic: "EPIC-23"
acceptance_criteria:
  - "Users can create a new Roster by pasting a list of names into a modal."
  - "Users can design a physical Room Template using an interactive 10x10 grid builder."
  - "Lesson modes are simplified to 'Sittplatsschema' and 'Gruppering' to reduce cognitive load."
  - "Newly created entities are immediately available in the selection gate."
---

## Context
The core planner (ST-23-03/04) was unusable because there was no UI to create the prerequisite data (Rosters and Room Templates). This story provides the entry points for teachers to populate their library.

## Implementation Details
- **Simplification**: Removed redundant lesson modes ('standard', 'test', 'lab') in favor of the two core functional variants.
- **Roster Builder**: Implemented bulk-paste parsing logic in `CreateRosterModal.vue`.
- **Room Builder**: Implemented a spatial toggle-grid in `CreateRoomTemplateModal.vue`.
- **UI Spec Fix**: Removed `translate-y` hover lifting effects from all selection buttons to comply with the project's static brutalist design specification.
