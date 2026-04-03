/**
 * Klassrumskartan entry shell tests.
 *
 * These tests verify that the public host shell surfaces the browser-owned
 * guest snapshot foundation honestly while the authenticated host still hands
 * off to the live planner view.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ClassroomPlannerEntryView from "./ClassroomPlannerEntryView.vue";

const loginModalMocks = vi.hoisted(() => ({
  open: vi.fn(),
}));

const guestSnapshotMocks = vi.hoisted(() => ({
  status: "missing" as "missing" | "ready" | "expired" | "loading" | "error" | "idle",
  summary: null as null | {
    snapshot_id: string;
    profile: "public_browser_workspace_with_upgrade";
    created_at: string;
    updated_at: string;
    expires_at: string;
    roster_count: number;
    template_count: number;
    smart_rule_set_count: number;
    checkpoint_count: number;
    has_grouping_draft: boolean;
    has_seating_draft: boolean;
  },
  errorMessage: null as string | null,
  isWorking: false,
  initializeGuestWorkspace: vi.fn(),
  clearGuestWorkspace: vi.fn(),
}));

vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("vue-router")>();
  return {
    ...actual,
    RouterLink: {
      props: ["to"],
      template: "<a :href='typeof to === \"string\" ? to : to.path'><slot /></a>",
    },
  };
});

vi.mock("../../composables/useLoginModal", () => ({
  useLoginModal: () => loginModalMocks,
}));

vi.mock("./useClassroomPlannerGuestSnapshotStatus", () => ({
  useClassroomPlannerGuestSnapshotStatus: () => guestSnapshotMocks,
}));

vi.mock("./ClassroomPlannerView.vue", () => ({
  default: {
    template: "<div data-test='live-classroom-planner'>Planner</div>",
  },
}));

describe("ClassroomPlannerEntryView", () => {
  beforeEach(() => {
    loginModalMocks.open.mockReset();
    guestSnapshotMocks.initializeGuestWorkspace.mockReset();
    guestSnapshotMocks.clearGuestWorkspace.mockReset();
    guestSnapshotMocks.status = "missing";
    guestSnapshotMocks.summary = null;
    guestSnapshotMocks.errorMessage = null;
    guestSnapshotMocks.isWorking = false;
  });

  it("renders the authenticated planner view for the authenticated host", () => {
    const wrapper = mount(ClassroomPlannerEntryView, {
      props: {
        hostMode: "authenticated",
      },
    });

    expect(wrapper.find("[data-test='live-classroom-planner']").exists()).toBe(true);
  });

  it("shows the missing guest workspace state and initializes storage on demand", async () => {
    const wrapper = mount(ClassroomPlannerEntryView, {
      props: {
        hostMode: "public",
      },
    });

    expect(wrapper.text()).toContain("Ingen lokal gästarbetsyta finns sparad");

    await wrapper.get("button.btn-primary").trigger("click");

    expect(guestSnapshotMocks.initializeGuestWorkspace).toHaveBeenCalledOnce();
  });

  it("shows the loading guest workspace state", () => {
    guestSnapshotMocks.status = "loading";

    const wrapper = mount(ClassroomPlannerEntryView, {
      props: {
        hostMode: "public",
      },
    });

    expect(wrapper.text()).toContain("Kontrollerar lokal gästarbetsyta");
  });

  it("shows the guest workspace error state", () => {
    guestSnapshotMocks.status = "error";
    guestSnapshotMocks.errorMessage = "Kunde inte läsa IndexedDB";

    const wrapper = mount(ClassroomPlannerEntryView, {
      props: {
        hostMode: "public",
      },
    });

    expect(wrapper.text()).toContain("Kunde inte läsa IndexedDB");
  });

  it("shows the expired guest workspace state", () => {
    guestSnapshotMocks.status = "expired";
    guestSnapshotMocks.summary = {
      snapshot_id: "guest-snapshot-1",
      profile: "public_browser_workspace_with_upgrade",
      created_at: "2026-04-04T08:00:00.000Z",
      updated_at: "2026-04-10T08:00:00.000Z",
      expires_at: "2026-04-18T08:00:00.000Z",
      roster_count: 0,
      template_count: 0,
      smart_rule_set_count: 0,
      checkpoint_count: 0,
      has_grouping_draft: false,
      has_seating_draft: false,
    };

    const wrapper = mount(ClassroomPlannerEntryView, {
      props: {
        hostMode: "public",
      },
    });

    expect(wrapper.text()).toContain("har gått ut");
    expect(wrapper.text()).toContain("2026-04-10T08:00:00.000Z");
  });

  it("shows the ready guest snapshot summary and can clear it", async () => {
    guestSnapshotMocks.status = "ready";
    guestSnapshotMocks.summary = {
      snapshot_id: "guest-snapshot-1",
      profile: "public_browser_workspace_with_upgrade",
      created_at: "2026-04-04T08:00:00.000Z",
      updated_at: "2026-04-04T08:00:00.000Z",
      expires_at: "2026-04-18T08:00:00.000Z",
      roster_count: 2,
      template_count: 1,
      smart_rule_set_count: 2,
      checkpoint_count: 1,
      has_grouping_draft: true,
      has_seating_draft: false,
    };

    const wrapper = mount(ClassroomPlannerEntryView, {
      props: {
        hostMode: "public",
      },
    });

    expect(wrapper.text()).toContain("guest-snapshot-1");
    expect(wrapper.text()).toContain("2 / 1");
    expect(wrapper.text()).toContain("Ja");
    expect(wrapper.text()).toContain("Nej");

    await wrapper.get("button.btn-ghost").trigger("click");

    expect(guestSnapshotMocks.clearGuestWorkspace).toHaveBeenCalledOnce();
  });

  it("shows the loading guest workspace state", () => {
    guestSnapshotMocks.status = "loading";

    const wrapper = mount(ClassroomPlannerEntryView, {
      props: {
        hostMode: "public",
      },
    });

    expect(wrapper.text()).toContain("Kontrollerar lokal gästarbetsyta");
  });

  it("shows the expired guest workspace state", async () => {
    guestSnapshotMocks.status = "expired";
    guestSnapshotMocks.summary = {
      snapshot_id: "guest-snapshot-1",
      profile: "public_browser_workspace_with_upgrade",
      created_at: "2026-04-04T08:00:00.000Z",
      updated_at: "2026-04-04T09:00:00.000Z",
      expires_at: "2026-04-18T08:00:00.000Z",
      roster_count: 0,
      template_count: 0,
      smart_rule_set_count: 0,
      checkpoint_count: 0,
      has_grouping_draft: false,
      has_seating_draft: false,
    };

    const wrapper = mount(ClassroomPlannerEntryView, {
      props: {
        hostMode: "public",
      },
    });

    expect(wrapper.text()).toContain("har gått ut");
    expect(wrapper.text()).toContain("2026-04-04T09:00:00.000Z");

    await wrapper.get("button.btn-primary").trigger("click");

    expect(guestSnapshotMocks.initializeGuestWorkspace).toHaveBeenCalledOnce();
  });

  it("shows the guest workspace error state", () => {
    guestSnapshotMocks.status = "error";
    guestSnapshotMocks.errorMessage = "Lokal lagring är inte tillgänglig.";

    const wrapper = mount(ClassroomPlannerEntryView, {
      props: {
        hostMode: "public",
      },
    });

    expect(wrapper.text()).toContain("Lokal lagring är inte tillgänglig.");
  });
});
