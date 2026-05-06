/**
 * Grouping workspace toolbar overflow tests.
 *
 * These tests freeze the visible-to-overflow migration order so grouping keeps
 * core phone actions visible while subordinate controls collapse.
 */

import { mount, type VueWrapper } from "@vue/test-utils";
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
      context: 842,
      smart: 714,
      reset: 620,
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

function expectInlineContributionHidden(wrapper: VueWrapper, selector: string): void {
  const contribution = wrapper.get(selector);
  expect(contribution.classes()).toContain("planner-toolbar-inline-overflowed");
  expect(contribution.attributes("data-overflow-inline-hidden")).toBe("true");
  expect(contribution.attributes("aria-hidden")).toBe("true");
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

  it("keeps context and Smart inline before the first cutoff", async () => {
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
    expect(wrapper.find('[data-test="grouping-overflow-roster-control"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="grouping-overflow-smart-control"]').exists()).toBe(false);
  }, 10_000);

  it("moves roster context into overflow before Smart", async () => {
    const wrapper = await mountToolbarForHidden(["context"]);

    expect(wrapper.find('[data-test="grouping-undo-redo-cluster"]').exists()).toBe(true);
    expectInlineContributionHidden(wrapper, '[data-test="grouping-roster-control"]');
    expect(wrapper.find('[data-test="grouping-smart-cluster"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="reset-grouping-draft"]').exists()).toBe(true);

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");

    expect(wrapper.get('[data-test="grouping-overflow-roster-control"]').classes()).not.toContain(
      "planner-toolbar-menu-panel-phone-only",
    );
    expect(wrapper.find('[data-test="grouping-overflow-smart-control"]').exists()).toBe(false);
  });

  it("moves Smart into overflow after roster context", async () => {
    const wrapper = await mountToolbarForHidden(["context", "smart"]);

    expect(wrapper.find('[data-test="grouping-undo-redo-cluster"]').exists()).toBe(true);
    expectInlineContributionHidden(wrapper, '[data-test="grouping-roster-control"]');
    expectInlineContributionHidden(wrapper, '[data-test="grouping-smart-cluster"]');
    expect(wrapper.find('[data-test="reset-grouping-draft"]').exists()).toBe(true);

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    expect(wrapper.get('[data-test="grouping-overflow-roster-control"]').classes()).not.toContain(
      "planner-toolbar-menu-panel-phone-only",
    );
    expect(wrapper.get('[data-test="grouping-overflow-smart-control"]').classes()).not.toContain(
      "planner-toolbar-menu-panel-phone-only",
    );
  });

  it("moves reset only after context and Smart have overflowed", async () => {
    const wrapper = await mountToolbarForHidden(["context", "smart", "reset"]);

    expect(wrapper.find('[data-test="new-grouping-draft"]').exists()).toBe(true);
    expectInlineContributionHidden(wrapper, '[data-test="grouping-roster-control"]');
    expectInlineContributionHidden(wrapper, '[data-test="grouping-smart-cluster"]');
    expectInlineContributionHidden(wrapper, '[data-overflow-contribution="reset"]');

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    expect(wrapper.find('[data-test="grouping-overflow-new-draft"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="grouping-overflow-roster-control"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-overflow-smart-control"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-overflow-reset"]').exists()).toBe(true);
  });
});
