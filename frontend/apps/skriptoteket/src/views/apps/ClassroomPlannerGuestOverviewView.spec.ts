/**
 * Klassrumskartan public guest overview view tests.
 *
 * These tests verify that the public empty-state shell keeps the final
 * user-facing registration copy while checkpoint-2 overview authoring is
 * available without exposing later planner lanes yet.
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
    show_roster_actions: true,
    show_template_actions: true,
  },
  isRosterModalOpen: false,
  isTemplateModalOpen: false,
  activeRosterModal: null,
  activeTemplateModal: null,
  overviewDeleteRosterTarget: null,
  overviewDeleteTemplateTarget: null,
  overviewDeleteRosterError: null,
  overviewDeleteTemplateError: null,
  isDeletingOverviewRoster: false,
  isDeletingOverviewTemplate: false,
  rosterImportPreviewApiPath:
    "/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview",
  selectWorkspaceRoster: vi.fn(),
  selectWorkspaceTemplate: vi.fn(),
  openRosterCreate: vi.fn(),
  closeRosterModal: vi.fn(),
  openSelectedRosterEdit: vi.fn(),
  openSelectedRosterDelete: vi.fn(),
  openTemplateCreate: vi.fn(),
  closeTemplateModal: vi.fn(),
  openOverviewTemplateEdit: vi.fn(),
  openSelectedTemplateDelete: vi.fn(),
  closeOverviewRosterDelete: vi.fn(),
  closeOverviewTemplateDelete: vi.fn(),
  saveRoster: vi.fn(),
  deleteRoster: vi.fn(),
  saveTemplate: vi.fn(),
  deleteTemplate: vi.fn(),
  applySavedRoster: vi.fn(),
  applyDeletedRoster: vi.fn(),
  applySavedTemplate: vi.fn(),
  applyDeletedTemplate: vi.fn(),
  confirmOverviewRosterDelete: vi.fn(),
  confirmOverviewTemplateDelete: vi.fn(),
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

vi.mock("./useClassroomPlannerGuestController", () => ({
  useClassroomPlannerGuestController: () => guestOverviewMocks,
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
      show_roster_actions: true,
      show_template_actions: true,
    };
  });

  it("keeps the final registration message while exposing checkpoint-2 overview authoring only", () => {
    const wrapper = mount(ClassroomPlannerGuestOverviewView);
    const normalizedText = wrapper.text().replace(/\s+/g, " ").trim();

    expect(normalizedText).toContain(
      "Vissa funktioner kräver att du registrerar ett konto. Tryck här för att skapa ett.",
    );
    expect(normalizedText).toContain("Börja med att skapa en klasslista.");
    expect(normalizedText).toContain("Behöver du mer vägledning kan du trycka på Hjälp.");
    expect(wrapper.findAll('[data-ui="segmented-toggle"] button')).toHaveLength(1);
    expect(wrapper.find("[data-test='overview-edit-roster']").exists()).toBe(true);
    expect(wrapper.find("[data-test='overview-edit-template']").exists()).toBe(true);
    expect(normalizedText).toContain("Ny klasslista");
    expect(normalizedText).toContain("Nytt klassrum");
    expect(normalizedText).not.toContain("Grupper");
    expect(normalizedText).not.toContain("Sittplatser");
    expect(normalizedText).not.toContain("Regler");
  });
});
