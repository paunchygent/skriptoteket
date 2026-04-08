/**
 * Klassrumskartan entry shell tests.
 *
 * These tests verify that the authenticated host keeps the existing planner
 * lane while the public host now resolves to the dedicated guest overview
 * shell instead of the earlier placeholder surface.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ClassroomPlannerEntryView from "./ClassroomPlannerEntryView.vue";

const guestUpgradeMocks = vi.hoisted(() => ({
  gateState: "allowed" as "allowed" | "checking" | "previewing" | "prompt" | "committing",
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
  previewReceipt: null as null | {
    mode: "preview" | "commit";
    snapshot_id: string;
    schema_version: number;
    submitted_snapshot_content_hash: string;
    server_snapshot_content_hash: string;
    created: unknown[];
    reused: unknown[];
    skipped: unknown[];
    conflicted: unknown[];
  },
  lastReceipt: null as null | {
    mode: "preview" | "commit";
    snapshot_id: string;
    schema_version: number;
    submitted_snapshot_content_hash: string;
    server_snapshot_content_hash: string;
    created: unknown[];
    reused: unknown[];
    skipped: unknown[];
    conflicted: unknown[];
  },
  errorMessage: null as string | null,
  isBlocking: false,
  shouldShowPrompt: false,
  importGuestWorkspace: vi.fn(),
  postponeGuestWorkspace: vi.fn(),
  dismissLastReceiptSummary: vi.fn(),
  discardGuestWorkspace: vi.fn(),
}));

vi.mock("./useClassroomPlannerGuestUpgrade", () => ({
  useClassroomPlannerGuestUpgrade: () => guestUpgradeMocks,
}));

vi.mock("./ClassroomPlannerView.vue", () => ({
  default: {
    template: "<div data-test='live-classroom-planner'>Planner</div>",
  },
}));

vi.mock("./ClassroomPlannerGuestOverviewView.vue", () => ({
  default: {
    template: "<div data-test='public-classroom-planner-overview'>Public guest overview</div>",
  },
}));

vi.mock("./ClassroomPlannerGuestUpgradePrompt.vue", () => ({
  default: {
    props: ["summary", "previewReceipt", "errorMessage"],
    template: `
      <div data-test="guest-upgrade-prompt">
        <button data-test="guest-upgrade-import" @click="$emit('import')">Import</button>
        <button data-test="guest-upgrade-postpone" @click="$emit('postpone')">Postpone</button>
        <button data-test="guest-upgrade-discard" @click="$emit('discard')">Discard</button>
      </div>
    `,
  },
}));

describe("ClassroomPlannerEntryView", () => {
  beforeEach(() => {
    guestUpgradeMocks.gateState = "allowed";
    guestUpgradeMocks.summary = null;
    guestUpgradeMocks.previewReceipt = null;
    guestUpgradeMocks.lastReceipt = null;
    guestUpgradeMocks.errorMessage = null;
    guestUpgradeMocks.isBlocking = false;
    guestUpgradeMocks.shouldShowPrompt = false;
    guestUpgradeMocks.importGuestWorkspace.mockReset();
    guestUpgradeMocks.postponeGuestWorkspace.mockReset();
    guestUpgradeMocks.dismissLastReceiptSummary.mockReset();
    guestUpgradeMocks.discardGuestWorkspace.mockReset();
  });

  it("renders the authenticated planner view for the authenticated host", () => {
    const wrapper = mount(ClassroomPlannerEntryView, {
      props: {
        hostMode: "authenticated",
      },
    });

    expect(wrapper.find("[data-test='live-classroom-planner']").exists()).toBe(true);
  });

  it("shows the authenticated guest-upgrade prompt as a modal over the live planner", async () => {
    guestUpgradeMocks.shouldShowPrompt = true;
    guestUpgradeMocks.summary = {
      snapshot_id: "guest-snapshot-1",
      profile: "public_browser_workspace_with_upgrade",
      created_at: "2026-04-04T08:00:00.000Z",
      updated_at: "2026-04-04T08:00:00.000Z",
      expires_at: "2026-04-18T08:00:00.000Z",
      roster_count: 1,
      template_count: 1,
      smart_rule_set_count: 0,
      checkpoint_count: 0,
      has_grouping_draft: true,
      has_seating_draft: false,
    };

    const wrapper = mount(ClassroomPlannerEntryView, {
      props: {
        hostMode: "authenticated",
      },
    });

    expect(wrapper.find("[data-test='guest-upgrade-prompt']").exists()).toBe(true);
    expect(wrapper.find("[data-test='live-classroom-planner']").exists()).toBe(true);

    await wrapper.get("[data-test='guest-upgrade-import']").trigger("click");
    await wrapper.get("[data-test='guest-upgrade-postpone']").trigger("click");
    await wrapper.get("[data-test='guest-upgrade-discard']").trigger("click");

    expect(guestUpgradeMocks.importGuestWorkspace).toHaveBeenCalledOnce();
    expect(guestUpgradeMocks.postponeGuestWorkspace).toHaveBeenCalledOnce();
    expect(guestUpgradeMocks.discardGuestWorkspace).toHaveBeenCalledOnce();
  });

  it("shows a dismissible post-import summary alongside the authenticated planner", async () => {
    guestUpgradeMocks.lastReceipt = {
      mode: "commit",
      snapshot_id: "guest-snapshot-1",
      schema_version: 1,
      submitted_snapshot_content_hash: "sha256:guest",
      server_snapshot_content_hash: "sha256:server",
      created: [{ entity_type: "roster", local_id: "roster-1" }],
      reused: [{ entity_type: "template", local_id: "template-1" }],
      skipped: [],
      conflicted: [],
    };

    const wrapper = mount(ClassroomPlannerEntryView, {
      props: {
        hostMode: "authenticated",
      },
    });

    expect(wrapper.find("[data-test='guest-upgrade-result-summary']").exists()).toBe(true);
    expect(wrapper.text()).toContain("Gästarbetsytan importerades till ditt konto");
    expect(wrapper.text()).toContain("guest-snapshot-1");
    expect(wrapper.find("[data-test='live-classroom-planner']").exists()).toBe(true);

    await wrapper.get("[data-test='guest-upgrade-result-dismiss']").trigger("click");

    expect(guestUpgradeMocks.dismissLastReceiptSummary).toHaveBeenCalledOnce();
  });

  it("keeps the post-import summary visible for mixed success and conflict receipts", () => {
    guestUpgradeMocks.lastReceipt = {
      mode: "commit",
      snapshot_id: "guest-snapshot-1",
      schema_version: 1,
      submitted_snapshot_content_hash: "sha256:guest",
      server_snapshot_content_hash: "sha256:server",
      created: [{ entity_type: "roster", local_id: "roster-1" }],
      reused: [],
      skipped: [],
      conflicted: [{ entity_type: "draft", local_id: "draft-grouping-1" }],
    };

    const wrapper = mount(ClassroomPlannerEntryView, {
      props: {
        hostMode: "authenticated",
      },
    });

    expect(wrapper.find("[data-test='guest-upgrade-result-summary']").exists()).toBe(true);
    expect(wrapper.text()).toContain("Konflikter");
  });

  it("does not render the post-import summary for an all-zero receipt", () => {
    guestUpgradeMocks.lastReceipt = {
      mode: "commit",
      snapshot_id: "guest-snapshot-1",
      schema_version: 1,
      submitted_snapshot_content_hash: "sha256:guest",
      server_snapshot_content_hash: "sha256:server",
      created: [],
      reused: [],
      skipped: [],
      conflicted: [],
    };

    const wrapper = mount(ClassroomPlannerEntryView, {
      props: {
        hostMode: "authenticated",
      },
    });

    expect(wrapper.find("[data-test='guest-upgrade-result-summary']").exists()).toBe(false);
    expect(wrapper.find("[data-test='live-classroom-planner']").exists()).toBe(true);
  });

  it("renders the dedicated public guest overview shell for the public host", () => {
    const wrapper = mount(ClassroomPlannerEntryView, {
      props: {
        hostMode: "public",
      },
    });

    expect(wrapper.find("[data-test='public-classroom-planner-overview']").exists()).toBe(true);
    expect(wrapper.find("[data-test='live-classroom-planner']").exists()).toBe(false);
  });
});
