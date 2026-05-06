/**
 * Seating workspace toolbar overflow tests.
 *
 * These tests freeze the seating-specific rendering contract for the shared
 * overflow ladder so toolbar collapse does not drift from grouping.
 */

import { mount, type VueWrapper } from "@vue/test-utils";
import { computed, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PlanDraft, RoomTemplate, Roster } from "../classroomPlannerTypes";

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
      context: 864,
      reset: 642,
      distribution: 500,
    })),
  }),
}));

vi.mock("../../../composables/useToast", () => ({
  useToast: () => toastMocks,
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

function expectInlineContributionHidden(wrapper: VueWrapper, selector: string): void {
  const contribution = wrapper.get(selector);
  expect(contribution.classes()).toContain("planner-toolbar-inline-overflowed");
  expect(contribution.attributes("data-overflow-inline-hidden")).toBe("true");
  expect(contribution.attributes("aria-hidden")).toBe("true");
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
    stateMocks.plannerState.setDraftSmartEnabled.mockReset();
    toastMocks.warning.mockReset();
    document.body.innerHTML = "";
  });

  it("keeps classroom context inline while advanced settings stays in the overflow menu", async () => {
    const wrapper = await mountToolbarForHidden([]);

    expect(wrapper.find('[data-test="seating-undo-redo-cluster"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="reset-seating-draft"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="new-seating-draft"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-workspace-setup"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-smart-cluster"]').exists()).toBe(false);

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");
    expect(wrapper.find('[data-test="seating-overflow-undo"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="seating-overflow-reset"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="seating-overflow-new-draft"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="seating-overflow-template-control"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="seating-overflow-open-settings"]').text()).toContain(
      "Avancerade inställningar",
    );
    expect(wrapper.get('[data-test="seating-overflow-open-settings"]').attributes("aria-haspopup")).toBe(
      "dialog",
    );
  }, 10_000);

  it("keeps share management in the secondary action cluster while lower-priority controls overflow", async () => {
    const wrapper = await mountToolbarForHidden(["context", "reset"]);
    await wrapper.setProps({
      showShareLinkAction: true,
      shares: [],
    });

    expect(wrapper.find('[data-test="seating-share-trigger"]').exists()).toBe(true);
    expectInlineContributionHidden(wrapper, '[data-test="seating-workspace-setup"]');
    expectInlineContributionHidden(wrapper, '[data-overflow-contribution="reset"]');

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");
    expect(wrapper.find('[data-test="seating-overflow-template-control"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-overflow-open-settings"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-overflow-share-trigger"]').exists()).toBe(false);
  });

  it("moves share management into overflow only after classroom context and reset", async () => {
    const wrapper = await mountToolbarForHidden(["context", "reset", "distribution"]);
    await wrapper.setProps({
      showShareLinkAction: true,
      shares: [],
    });

    expectInlineContributionHidden(wrapper, '[data-test="seating-workspace-setup"]');
    expectInlineContributionHidden(wrapper, '[data-overflow-contribution="reset"]');
    expectInlineContributionHidden(wrapper, '[data-overflow-contribution="distribution"]');

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");
    expect(wrapper.find('[data-test="seating-overflow-template-control"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-overflow-reset"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-overflow-share-trigger"]').exists()).toBe(true);
  });

  it("keeps advanced settings in the menu when classroom context also overflows", async () => {
    const wrapper = await mountToolbarForHidden(["context"]);

    expect(wrapper.find('[data-test="seating-undo-redo-cluster"]').exists()).toBe(true);
    expectInlineContributionHidden(wrapper, '[data-test="seating-workspace-setup"]');
    expect(wrapper.find('[data-test="reset-seating-draft"]').exists()).toBe(true);

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");

    expect(wrapper.get('[data-test="seating-overflow-template-control"]').classes()).not.toContain(
      "planner-toolbar-menu-panel-phone-only",
    );
    expect(wrapper.find('[data-test="seating-overflow-open-settings"]').exists()).toBe(true);
  });

  it("routes advanced settings through the settings menu item", async () => {
    const wrapper = await mountToolbarForHidden([]);

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");
    await wrapper.get('[data-test="seating-overflow-open-settings"]').trigger("click");

    expect(wrapper.emitted("open-settings")).toEqual([[]]);
    expect(stateMocks.plannerState.setDraftSmartEnabled).not.toHaveBeenCalled();
    expect(toastMocks.warning).not.toHaveBeenCalled();
  });

  it("keeps reset overflow separate from the settings menu item", async () => {
    const wrapper = await mountToolbarForHidden(["context"]);

    expect(wrapper.find('[data-test="seating-undo-redo-cluster"]').exists()).toBe(true);
    expectInlineContributionHidden(wrapper, '[data-test="seating-workspace-setup"]');
    expect(wrapper.find('[data-test="reset-seating-draft"]').exists()).toBe(true);

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");
    expect(wrapper.get('[data-test="seating-overflow-template-control"]').classes()).not.toContain(
      "planner-toolbar-menu-panel-phone-only",
    );
    expect(wrapper.find('[data-test="seating-overflow-open-settings"]').exists()).toBe(true);
  });

  it("moves seating reset only after classroom context has overflowed", async () => {
    const wrapper = await mountToolbarForHidden(["context", "reset"]);

    expect(wrapper.find('[data-test="new-seating-draft"]').exists()).toBe(true);
    expectInlineContributionHidden(wrapper, '[data-test="seating-workspace-setup"]');
    expectInlineContributionHidden(wrapper, '[data-overflow-contribution="reset"]');

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");
    expect(wrapper.find('[data-test="seating-overflow-new-draft"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="seating-overflow-template-control"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-overflow-open-settings"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seating-overflow-reset"]').exists()).toBe(true);
  });
});
