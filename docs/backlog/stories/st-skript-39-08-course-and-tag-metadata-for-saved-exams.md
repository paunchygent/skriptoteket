---
type: story
id: ST-SKRIPT-39-08
title: Course and tag metadata for saved exams
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-13'
status: proposed
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-39
acceptance_criteria:
- A teacher can give each saved exam an official course and tags from that subject's
  fixed list, choose their own courses in the profile, have the import suggest course
  and tags, and sort saved exams by course, date and class
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

## Contract Inputs

- User decisions 2026-10-16 (TASK-SKRIPT-39-05-14 planning): the teacher
  selects a course (gymnasiet) or a subject (grundskolan); for gymnasiet the
  subject follows from the course. Valid courses and subjects come from
  Skolverket's registers. The choice is a simple dropdown that doubles as a
  search field in the import panel, and it can be changed after conversion in
  a metadata panel together with the Mina filer file name and the exam title
  used in the QTI data. This story's first task builds that dropdown, the
  course list and the metadata panel; TASK-SKRIPT-39-05-14 leaves a raw course
  hint from the source document for the dropdown to preselect from. Mina filer
  renaming follows ST-SKRIPT-37-05.

## Tasks

## Verification

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
