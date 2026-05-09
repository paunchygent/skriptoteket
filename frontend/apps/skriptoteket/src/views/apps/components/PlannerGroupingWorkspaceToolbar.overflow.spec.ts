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
const toastMocks = vi.hoisted(() => ({
  warning: vi.fn(),
}));

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
      reset: 620,
      distribution: 480,
    })),
  }),
}));

vi.mock("../../../composables/useToast", () => ({
  useToast: () => toastMocks,
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
    stateMocks.plannerState.setDraftSmartEnabled.mockReset();
    toastMocks.warning.mockReset();
    document.body.innerHTML = "";
  });

  it("keeps context inline while advanced settings stays in the overflow menu", async () => {
    const wrapper = await mountToolbarForHidden([]);

    expect(wrapper.find('[data-test="grouping-undo-redo-cluster"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="reset-grouping-draft"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="new-grouping-draft"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-roster-control"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-smart-cluster"]').exists()).toBe(false);

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    expect(wrapper.find('[data-test="grouping-overflow-undo"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="grouping-overflow-reset"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="grouping-overflow-new-draft"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="grouping-overflow-roster-control"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="grouping-overflow-open-settings"]').text()).toContain(
      "Avancerade inställningar",
    );
    expect(wrapper.get('[data-test="grouping-overflow-open-settings"]').attributes("aria-haspopup")).toBe(
      "dialog",
    );
  }, 10_000);

  it("keeps advanced settings in the menu when roster context also overflows", async () => {
    const wrapper = await mountToolbarForHidden(["context"]);
    await wrapper.setProps({
      showShareLinkAction: true,
      shares: [],
    });

    expect(wrapper.find('[data-test="grouping-undo-redo-cluster"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-share-trigger"]').exists()).toBe(true);
    expectInlineContributionHidden(wrapper, '[data-test="grouping-roster-control"]');
    expect(wrapper.find('[data-test="reset-grouping-draft"]').exists()).toBe(true);

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");

    expect(wrapper.get('[data-test="grouping-overflow-roster-control"]').classes()).not.toContain(
      "planner-toolbar-menu-panel-phone-only",
    );
    expect(wrapper.find('[data-test="grouping-overflow-open-settings"]').exists()).toBe(true);
  });

  it("keeps share management inline while class and reset controls overflow", async () => {
    const wrapper = await mountToolbarForHidden(["context", "reset"]);
    await wrapper.setProps({
      showShareLinkAction: true,
      shares: [],
    });

    expect(wrapper.find('[data-test="grouping-share-trigger"]').exists()).toBe(true);
    expectInlineContributionHidden(wrapper, '[data-test="grouping-roster-control"]');
    expectInlineContributionHidden(wrapper, '[data-overflow-contribution="reset"]');

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    expect(wrapper.find('[data-test="grouping-overflow-roster-control"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-overflow-share-trigger"]').exists()).toBe(false);
  });

  it("moves share management into overflow only after context and reset", async () => {
    const wrapper = await mountToolbarForHidden(["context", "reset", "distribution"]);
    await wrapper.setProps({
      showShareLinkAction: true,
      shares: [],
    });

    expectInlineContributionHidden(wrapper, '[data-test="grouping-roster-control"]');
    expectInlineContributionHidden(wrapper, '[data-overflow-contribution="reset"]');
    expectInlineContributionHidden(wrapper, '[data-overflow-contribution="distribution"]');

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    expect(wrapper.find('[data-test="grouping-overflow-roster-control"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-overflow-reset"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-overflow-share-trigger"]').exists()).toBe(true);
  });

  it("keeps the group-count split control reachable when phone distribution overflows", async () => {
    stateMocks.plannerState.groups = [
      { id: "group-1", name: "Grupp 1", sort_order: 0, name_is_custom: false },
      { id: "group-2", name: "Grupp 2", sort_order: 1, name_is_custom: false },
    ];
    const wrapper = await mountToolbarForHidden(["context", "reset", "distribution"]);
    await wrapper.setProps({
      showShareLinkAction: true,
      shares: [],
    });

    expect(wrapper.find('[data-test="grouping-group-count-control"]').exists()).toBe(true);
    expect(wrapper.get('[data-test="decrement-group-count"]').attributes("disabled")).toBeUndefined();
    expect(wrapper.get('[data-test="group-count-value"]').text()).toBe("2");
    expect(wrapper.get('[data-test="increment-group-count"]').attributes("disabled")).toBeUndefined();
    expectInlineContributionHidden(wrapper, '[data-overflow-contribution="distribution"]');

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    expect(wrapper.find('[data-test="grouping-overflow-share-trigger"]').exists()).toBe(true);
  });

  it("routes advanced settings through the settings menu item", async () => {
    const wrapper = await mountToolbarForHidden([]);

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    await wrapper.get('[data-test="grouping-overflow-open-settings"]').trigger("click");

    expect(wrapper.emitted("open-settings")).toEqual([[]]);
    expect(stateMocks.plannerState.setDraftSmartEnabled).not.toHaveBeenCalled();
    expect(toastMocks.warning).not.toHaveBeenCalled();
  });

  it("keeps reset overflow separate from the settings menu item", async () => {
    const wrapper = await mountToolbarForHidden(["context"]);

    expect(wrapper.find('[data-test="grouping-undo-redo-cluster"]').exists()).toBe(true);
    expectInlineContributionHidden(wrapper, '[data-test="grouping-roster-control"]');
    expect(wrapper.find('[data-test="reset-grouping-draft"]').exists()).toBe(true);

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    expect(wrapper.get('[data-test="grouping-overflow-roster-control"]').classes()).not.toContain(
      "planner-toolbar-menu-panel-phone-only",
    );
    expect(wrapper.find('[data-test="grouping-overflow-open-settings"]').exists()).toBe(true);
  });

  it("moves reset only after context has overflowed", async () => {
    const wrapper = await mountToolbarForHidden(["context", "reset"]);

    expect(wrapper.find('[data-test="new-grouping-draft"]').exists()).toBe(true);
    expectInlineContributionHidden(wrapper, '[data-test="grouping-roster-control"]');
    expectInlineContributionHidden(wrapper, '[data-overflow-contribution="reset"]');

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    expect(wrapper.find('[data-test="grouping-overflow-new-draft"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="grouping-overflow-roster-control"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-overflow-open-settings"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="grouping-overflow-reset"]').exists()).toBe(true);
  });
});
