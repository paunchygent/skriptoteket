/**
 * Seating workspace toolbar overflow tests.
 *
 * These tests freeze the seating-specific rendering contract for the shared
 * overflow ladder so toolbar collapse does not drift from grouping.
 */

import { mount } from "@vue/test-utils";
import { computed, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PlanDraft, RoomTemplate, Roster } from "../classroomPlannerTypes";

const hiddenContributionIds = ref<string[]>([]);

vi.mock("./usePlannerToolbarOverflow", () => ({
  usePlannerToolbarOverflow: () => ({
    hiddenContributionIds,
    stageLabel: computed(() =>
      hiddenContributionIds.value.length === 0
        ? "all-visible"
        : `${hiddenContributionIds.value.join("-")}-overflow`,
    ),
    thresholds: computed(() => ({
      "undo-redo": 864,
      reset: 790,
      "new-draft": 702,
      context: 628,
    })),
  }),
}));

type PlannerStateMock = {
  template: RoomTemplate | null;
  draft: (Pick<PlanDraft, "id" | "draft_kind" | "revision"> & {
    smart_enabled?: boolean;
    use_history?: boolean;
  }) | null;
  students: Roster["students"];
  seats: RoomTemplate["seats"];
  seatAssignments: Array<{ student_id: string; seat_id: string }>;
  isWorkspaceBusy: boolean;
  isRunningSmartSeating: boolean;
  canUndo: boolean;
  canRedo: boolean;
  undoSeatingDraft: ReturnType<typeof vi.fn>;
  redoSeatingDraft: ReturnType<typeof vi.fn>;
  runSeatingShuffle: ReturnType<typeof vi.fn>;
  clearSeatingAssignments: ReturnType<typeof vi.fn>;
  setDraftSmartEnabled: ReturnType<typeof vi.fn>;
};

const stateMocks = vi.hoisted(() => ({
  plannerState: ((): PlannerStateMock => ({
    template: {
      id: "template-1",
      name: "Sal 101",
      seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
      fixtures: [],
    },
    draft: {
      id: "draft-1",
      draft_kind: "seating",
      revision: 2,
      smart_enabled: true,
      use_history: true,
    },
    students: [{ id: "student-1", display_name: "Ada Lovelace" }],
    seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
    seatAssignments: [{ student_id: "student-1", seat_id: "seat-1" }],
    isWorkspaceBusy: false,
    isRunningSmartSeating: false,
    canUndo: true,
    canRedo: true,
    undoSeatingDraft: vi.fn(),
    redoSeatingDraft: vi.fn(),
    runSeatingShuffle: vi.fn(),
    clearSeatingAssignments: vi.fn(),
    setDraftSmartEnabled: vi.fn(),
  }))(),
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

function buildTemplate(): RoomTemplate {
  return {
    id: "template-1",
    name: "Sal 101",
    seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
    fixtures: [],
  };
}

async function mountToolbarForHidden(
  ids: string[],
) {
  hiddenContributionIds.value = ids;
  const module = await import("./PlannerSeatingWorkspaceToolbar.vue");
  return mount(module.default, {
    props: {
      availableTemplates: [buildTemplate()],
      selectedTemplateId: "template-1",
    },
    attachTo: document.body,
  });
}

describe("PlannerSeatingWorkspaceToolbar overflow", () => {
  beforeEach(() => {
    stateMocks.plannerState.template = buildTemplate();
    stateMocks.plannerState.seatAssignments = [{ student_id: "student-1", seat_id: "seat-1" }];
    stateMocks.plannerState.isWorkspaceBusy = false;
    stateMocks.plannerState.isRunningSmartSeating = false;
    stateMocks.plannerState.canUndo = true;
    stateMocks.plannerState.canRedo = true;
    stateMocks.plannerState.undoSeatingDraft.mockReset();
    stateMocks.plannerState.redoSeatingDraft.mockReset();
    document.body.innerHTML = "";
  });

  it("keeps undo/redo and reset inline before the first seating cutoff", async () => {
    const wrapper = await mountToolbarForHidden([]);

    expect(wrapper.find('[data-test="seating-undo-redo-cluster"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="reset-seating-draft"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="new-seating-draft"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-workspace-setup"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-smart-cluster"]').exists()).toBe(false);

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");
    expect(wrapper.find('[data-test="seating-overflow-undo"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="seating-overflow-reset"]').classes()).toContain(
      "planner-toolbar-menu-item-phone-only",
    );
    expect(wrapper.find('[data-test="seating-overflow-new-draft"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="seating-overflow-smart-control"]').exists()).toBe(true);
  }, 10_000);

  it("keeps share management in the secondary action cluster while lower-priority controls overflow", async () => {
    const wrapper = await mountToolbarForHidden(["undo-redo", "reset", "new-draft", "context"]);
    await wrapper.setProps({
      showShareLinkAction: true,
      shares: [],
    });

    expect(wrapper.find('[data-test="seating-share-trigger"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-workspace-setup"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="seating-smart-cluster"]').exists()).toBe(false);

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");
    expect(wrapper.find('[data-test="seating-overflow-template-control"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-overflow-smart-control"]').exists()).toBe(true);
  });

  it("keeps seating undo/redo inline even when the measured overflow state is narrow", async () => {
    const wrapper = await mountToolbarForHidden(["undo-redo"]);

    expect(wrapper.find('[data-test="seating-undo-redo-cluster"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="reset-seating-draft"]').exists()).toBe(true);

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");

    expect(wrapper.find('[data-test="seating-overflow-undo"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="seating-overflow-redo"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="seating-overflow-reset"]').classes()).toContain(
      "planner-toolbar-menu-item-phone-only",
    );
  });

  it("moves seating reset into overflow without hiding undo/redo", async () => {
    const wrapper = await mountToolbarForHidden(["undo-redo", "reset"]);

    expect(wrapper.find('[data-test="seating-undo-redo-cluster"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="reset-seating-draft"]').exists()).toBe(false);

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");
    expect(wrapper.find('[data-test="seating-overflow-undo"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="seating-overflow-redo"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="seating-overflow-reset"]').exists()).toBe(true);
    expect(wrapper.get('[data-test="seating-overflow-reset"]').classes()).not.toContain(
      "planner-toolbar-menu-item-phone-only",
    );
  });

  it("keeps new seating draft inline while classroom context can move into overflow", async () => {
    const wrapper = await mountToolbarForHidden(["undo-redo", "reset", "new-draft", "context"]);

    expect(wrapper.find('[data-test="new-seating-draft"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-workspace-setup"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="seating-smart-cluster"]').exists()).toBe(false);

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");
    expect(wrapper.find('[data-test="seating-overflow-new-draft"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="seating-overflow-template-control"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-overflow-smart-control"]').exists()).toBe(true);
  });
});
