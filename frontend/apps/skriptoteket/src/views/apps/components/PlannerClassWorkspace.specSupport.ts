/**
 * Shared fixtures and mount helpers for the PlannerClassWorkspace specs.
 */

import { mount } from "@vue/test-utils";

import type { RoomTemplate } from "../classroomPlannerTypes";
import PlannerClassWorkspace from "./PlannerClassWorkspace.vue";

export const groupingShare = {
  id: "share-1",
  title: "SA24D grupper",
  draft_kind: "grouping",
  source: "public_guest",
  source_revision: 1,
  slug: "sa24d-grupper",
  public_path: "/share/classroom/sa24d-grupper",
  public_url: "https://skriptoteket.example/share/classroom/sa24d-grupper",
  preview_description: "Gruppindelning",
  renderer_version: "klassrumskartan-share-renderer-v1",
  presentation_schema_version: "grouping-share-v1",
  content_hash: "sha256:content",
  presentation_hash: "sha256:presentation",
  created_at: "2026-05-06T08:00:00Z",
  updated_at: "2026-05-06T08:00:00Z",
  revoked_at: null,
  expires_at: "2026-06-06T08:00:00Z",
};

export function buildWorkspaceSummary() {
  return {
    roster: { id: "roster-1", name: "SA24D", student_count: 28 },
    task_entry_options: [
      { draft_kind: "grouping" as const, classroom_selection_mode: "optional" as const },
      { draft_kind: "seating" as const, classroom_selection_mode: "optional" as const },
    ],
    active_grouping_draft: null,
    active_seating_draft: null,
    grouping_history: [],
    seating_history: [],
  };
}

export function buildRosters() {
  return [
    { id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] },
    { id: "roster-2", name: "NA25A", students: [{ id: "s2", display_name: "Bo" }] },
  ];
}

export function buildTemplates(): RoomTemplate[] {
  return [
    {
      id: "template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: [{ id: "seat-1", x: 96, y: 96, zone: "front" }],
      fixtures: [
        {
          id: "door-1",
          type: "door",
          x: 0,
          y: 96,
          width: 96,
          height: 96,
          label: null,
        },
      ],
    },
    {
      id: "template-2",
      name: "Sal 202",
      grid_cols: 12,
      grid_rows: 8,
      seats: [{ id: "seat-2", x: 192, y: 192, zone: "middle" }],
      fixtures: [],
    },
  ];
}

export function mountWorkspace(props?: Record<string, unknown>) {
  return mount(PlannerClassWorkspace, {
    props: {
      isLoadingWorkspace: false,
      workspaceSummary: buildWorkspaceSummary(),
      availableRosters: buildRosters(),
      availableTemplates: buildTemplates(),
      selectedRosterId: "roster-1",
      selectedTemplateId: "template-1",
      visibleGroupingDraft: null,
      visibleSeatingDraft: null,
      ...props,
    },
  });
}

export function findWorkspaceToggle(
  wrapper: ReturnType<typeof mountWorkspace>,
  label: "Grupper" | "Sittplatser" | "Regler",
) {
  const button = wrapper.findAll('[data-ui="segmented-toggle"] button').find(
    (candidate) => candidate.text() === label,
  );
  if (!button) {
    throw new Error(`Expected the segmented toggle to expose ${label}.`);
  }
  return button;
}
