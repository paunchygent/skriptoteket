/**
 * Seating workspace toolbar phone label tests.
 *
 * These tests freeze the narrow-width label contract for the two Sittplatser
 * toolbar controls that wrapped at 390 px: the new-draft button and the
 * "Avancerade inställningar" overflow item (TASK-SKRIPT-REP-0058).
 */

import { mount } from "@vue/test-utils";
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

const PHONE_VIEWPORT_QUERY = "(max-width: 767px)";

/**
 * jsdom has no layout; the shared setup stub matches every query. These tests
 * name the phone band explicitly so the two compositions are distinguishable.
 */
function stubViewport(isPhone: boolean): void {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: (query: string) => ({
      matches: isPhone && query === PHONE_VIEWPORT_QUERY,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  });
}

function buildTemplate(): RoomTemplate {
  return {
    id: "template-1",
    name: "Sal 101",
    seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
    fixtures: [],
  };
}

async function mountToolbar() {
  hiddenContributionIds.value = [];
  const module = await import("./PlannerSeatingWorkspaceToolbar.vue");
  return mount(module.default, {
    props: {
      availableTemplates: [buildTemplate()],
      selectedTemplateId: "template-1",
    },
    attachTo: document.body,
  });
}

describe("PlannerSeatingWorkspaceToolbar phone labels", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("uses the narrow-width label and keeps the new-draft label on one line on a phone", async () => {
    stubViewport(true);
    const wrapper = await mountToolbar();

    const button = wrapper.get('[data-test="new-seating-draft"]');
    expect(button.classes()).toContain("whitespace-nowrap");
    expect(button.text()).toBe("Nytt");
    expect(button.attributes("aria-label")).toBe("Nytt utkast");
    expect(button.find("svg").exists()).toBe(true);

    wrapper.unmount();
  });

  it("keeps the full new-draft label on tablet and desktop", async () => {
    stubViewport(false);
    const wrapper = await mountToolbar();

    const button = wrapper.get('[data-test="new-seating-draft"]');
    expect(button.classes()).toContain("whitespace-nowrap");
    expect(button.text()).toBe("Nytt utkast");

    wrapper.unmount();
  });

  it("sizes the overflow menu to its longest item without wrapping its label", async () => {
    stubViewport(true);
    const wrapper = await mountToolbar();

    await wrapper.get('[data-test="seating-actions-menu"]').trigger("click");

    const item = wrapper.get('[data-test="seating-overflow-open-settings"]');
    expect(item.text()).toBe("Avancerade inställningar");
    expect(item.get("span").classes()).toContain("whitespace-nowrap");

    const menu = wrapper.get('[role="menu"]');
    expect(menu.classes()).toContain("w-max");
    expect(menu.classes()).toContain("max-w-[calc(100vw-2*var(--huleedu-space-4))]");

    wrapper.unmount();
  });
});
