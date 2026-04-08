/**
 * Grouping workspace toolbar overflow tests.
 *
 * These tests freeze the visible-to-overflow migration order so grouping uses
 * the exact `undo` / `redo` then `Börja om` collapse ladder.
 */

import { mount } from "@vue/test-utils";
import { computed, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DraftGroup, PlanDraft, Roster } from "../classroomPlannerTypes";

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
      "undo-redo": 842,
      reset: 772,
      "new-draft": 684,
      context: 612,
      smart: 540,
    })),
  }),
}));

type PlannerStateMock = {
  draft: (Pick<PlanDraft, "id" | "draft_kind" | "revision"> & {
    smart_enabled?: boolean;
    use_history?: boolean;
    grouping_seating_distance_enabled?: boolean;
  }) | null;
  groupAssignments: Array<{ student_id: string; group_id: string }>;
  groups: DraftGroup[];
  isWorkspaceBusy: boolean;
  canUndo: boolean;
  canRedo: boolean;
  undoGroupingDraft: ReturnType<typeof vi.fn>;
  redoGroupingDraft: ReturnType<typeof vi.fn>;
  runGroupingShuffle: ReturnType<typeof vi.fn>;
  clearGroupingAssignments: ReturnType<typeof vi.fn>;
  addGroup: ReturnType<typeof vi.fn>;
  removeGroup: ReturnType<typeof vi.fn>;
  setDraftSmartEnabled: ReturnType<typeof vi.fn>;
};

const stateMocks = vi.hoisted(() => ({
  plannerState: ((): PlannerStateMock => ({
    draft: {
      id: "draft-1",
      draft_kind: "grouping",
      revision: 2,
      smart_enabled: true,
      use_history: true,
      grouping_seating_distance_enabled: true,
    },
    groupAssignments: [{ student_id: "student-1", group_id: "group-1" }],
    groups: [{ id: "group-1", name: "Grupp 1", sort_order: 0, name_is_custom: false }],
    isWorkspaceBusy: false,
    canUndo: true,
    canRedo: true,
    undoGroupingDraft: vi.fn(),
    redoGroupingDraft: vi.fn(),
    runGroupingShuffle: vi.fn(),
    clearGroupingAssignments: vi.fn(),
    addGroup: vi.fn(),
    removeGroup: vi.fn(),
    setDraftSmartEnabled: vi.fn(),
  }))(),
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

function buildRosters(): Roster[] {
  return [{ id: "roster-1", name: "SA24D", students: [] }];
}

async function mountToolbarForHidden(
  ids: string[],
) {
  hiddenContributionIds.value = ids;
  const module = await import("./PlannerGroupingWorkspaceToolbar.vue");
  return mount(module.default, {
    props: {
      availableRosters: buildRosters(),
      selectedRosterId: "roster-1",
    },
    attachTo: document.body,
  });
}

describe("PlannerGroupingWorkspaceToolbar overflow", () => {
  beforeEach(() => {
    stateMocks.plannerState.groupAssignments = [{ student_id: "student-1", group_id: "group-1" }];
    stateMocks.plannerState.isWorkspaceBusy = false;
    stateMocks.plannerState.canUndo = true;
    stateMocks.plannerState.canRedo = true;
    stateMocks.plannerState.undoGroupingDraft.mockReset();
    stateMocks.plannerState.redoGroupingDraft.mockReset();
    document.body.innerHTML = "";
  });

  it("keeps undo/redo and reset inline before the first cutoff", async () => {
    const wrapper = await mountToolbarForHidden([]);

    expect(wrapper.find('[data-test="grouping-undo-redo-cluster"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="reset-grouping-draft"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="new-grouping-draft"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-roster-control"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-smart-cluster"]').exists()).toBe(true);

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    expect(wrapper.find('[data-test="grouping-overflow-undo"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="grouping-overflow-reset"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="grouping-overflow-new-draft"]').exists()).toBe(false);
  });

  it("moves undo/redo into overflow before reset", async () => {
    const wrapper = await mountToolbarForHidden(["undo-redo"]);

    expect(wrapper.find('[data-test="grouping-undo-redo-cluster"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="reset-grouping-draft"]').exists()).toBe(true);

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    await wrapper.get('[data-test="grouping-overflow-undo"]').trigger("click");
    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    await wrapper.get('[data-test="grouping-overflow-redo"]').trigger("click");

    expect(stateMocks.plannerState.undoGroupingDraft).toHaveBeenCalledTimes(1);
    expect(stateMocks.plannerState.redoGroupingDraft).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="grouping-overflow-reset"]').exists()).toBe(false);
  });

  it("moves reset into overflow only after undo/redo have already collapsed", async () => {
    const wrapper = await mountToolbarForHidden(["undo-redo", "reset"]);

    expect(wrapper.find('[data-test="grouping-undo-redo-cluster"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="reset-grouping-draft"]').exists()).toBe(false);

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    expect(wrapper.find('[data-test="grouping-overflow-undo"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-overflow-redo"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-overflow-reset"]').exists()).toBe(true);
  });

  it("can move new draft, roster context, and smart controls into overflow after reset", async () => {
    const wrapper = await mountToolbarForHidden(["undo-redo", "reset", "new-draft", "context", "smart"]);

    expect(wrapper.find('[data-test="new-grouping-draft"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="grouping-roster-control"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="grouping-smart-cluster"]').exists()).toBe(false);

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    expect(wrapper.find('[data-test="grouping-overflow-new-draft"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-overflow-roster-control"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-overflow-smart-control"]').exists()).toBe(true);
  });
});
