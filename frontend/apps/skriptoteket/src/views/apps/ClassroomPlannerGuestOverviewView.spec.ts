/**
 * Klassrumskartan public guest overview view tests.
 *
 * These tests verify that the public empty-state shell keeps the final
 * user-facing registration copy while unfinished guest actions stay hidden
 * until later checkpoints land.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ClassroomPlannerGuestOverviewView from "./ClassroomPlannerGuestOverviewView.vue";

const routerMocks = vi.hoisted(() => ({
  push: vi.fn(),
}));

const guestOverviewMocks = vi.hoisted(() => ({
  availableRosters: [],
  availableTemplates: [],
  selectedRosterId: null,
  selectedTemplateId: null,
  isBootstrapping: false,
  bootstrapError: null,
  plannerActionError: null,
  classWorkspaceSummary: null,
  overviewCapabilities: {
    show_grouping_option: false,
    show_seating_option: false,
    show_rules_option: false,
    show_roster_actions: false,
    show_template_actions: false,
  },
  selectWorkspaceRoster: vi.fn(),
  selectWorkspaceTemplate: vi.fn(),
}));

vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("vue-router")>();
  return {
    ...actual,
    RouterLink: {
      props: ["to"],
      template: "<a :href='typeof to === \"string\" ? to : to.path'><slot /></a>",
    },
    useRouter: () => routerMocks,
  };
});

vi.mock("./useClassroomPlannerGuestOverviewShell", () => ({
  useClassroomPlannerGuestOverviewShell: () => guestOverviewMocks,
}));

describe("ClassroomPlannerGuestOverviewView", () => {
  beforeEach(() => {
    routerMocks.push.mockReset();
    guestOverviewMocks.selectWorkspaceRoster.mockReset();
    guestOverviewMocks.selectWorkspaceTemplate.mockReset();
    guestOverviewMocks.availableRosters = [];
    guestOverviewMocks.availableTemplates = [];
    guestOverviewMocks.selectedRosterId = null;
    guestOverviewMocks.selectedTemplateId = null;
    guestOverviewMocks.isBootstrapping = false;
    guestOverviewMocks.bootstrapError = null;
    guestOverviewMocks.plannerActionError = null;
    guestOverviewMocks.classWorkspaceSummary = null;
    guestOverviewMocks.overviewCapabilities = {
      show_grouping_option: false,
      show_seating_option: false,
      show_rules_option: false,
      show_roster_actions: false,
      show_template_actions: false,
    };
  });

  it("keeps the final registration message while hiding unfinished guest actions in the empty state", () => {
    const wrapper = mount(ClassroomPlannerGuestOverviewView);
    const normalizedText = wrapper.text().replace(/\s+/g, " ").trim();

    expect(normalizedText).toContain(
      "Vissa funktioner kräver att du registrerar ett konto. Tryck här för att skapa ett.",
    );
    expect(normalizedText).toContain("Börja med att skapa en klasslista.");
    expect(normalizedText).toContain("Behöver du mer vägledning kan du trycka på Hjälp.");
    expect(wrapper.findAll('[data-ui="segmented-toggle"] button')).toHaveLength(1);
    expect(wrapper.find("[data-test='overview-edit-roster']").exists()).toBe(false);
    expect(wrapper.find("[data-test='overview-edit-template']").exists()).toBe(false);
    expect(normalizedText).not.toContain("Ny klasslista");
    expect(normalizedText).not.toContain("Nytt klassrum");
    expect(normalizedText).not.toContain("Grupper");
    expect(normalizedText).not.toContain("Sittplatser");
    expect(normalizedText).not.toContain("Regler");
  });
});
