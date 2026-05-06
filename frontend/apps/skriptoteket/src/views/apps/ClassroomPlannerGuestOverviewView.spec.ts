/**
 * Klassrumskartan public guest view tests.
 *
 * These tests verify that the public shell keeps the final registration copy,
 * enables checkpoint-3 guest grouping/seating entry points on the class
 * workspace, and swaps to the dedicated guest planner shell when a guest draft
 * is active.
 */

import { defineComponent, nextTick } from "vue";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import ClassroomPlannerGuestOverviewView from "./ClassroomPlannerGuestOverviewView.vue";

const routerMocks = vi.hoisted(() => ({
  push: vi.fn(),
}));

const shareArtifact = {
  id: "share-1",
  title: "SA24D",
  draft_kind: "grouping",
  source: "public_guest",
  source_revision: 1,
  slug: "sa24d",
  public_path: "/share/classroom/public/sa24d",
  public_url: "https://skriptoteket.hule.education/share/classroom/public/sa24d",
  preview_description: "Publik gruppindelning",
  renderer_version: "klassrumskartan-share-renderer-v1",
  presentation_schema_version: "grouping-share-v1",
  content_hash: "sha256:content",
  presentation_hash: "sha256:presentation",
  created_at: "2026-05-06T08:00:00Z",
  updated_at: "2026-05-06T08:00:00Z",
  revoked_at: null,
  expires_at: "2026-06-06T08:00:00Z",
};

const publicFlowMocks = vi.hoisted(() => ({
  groupingExport: {
    isBusy: { value: false },
    statusLabel: { value: null as string | null },
    errorMessage: { value: null as string | null },
    startDefaultExport: vi.fn(),
    startExport: vi.fn(),
  },
  seatingExport: {
    isBusy: { value: false },
    statusLabel: { value: null as string | null },
    errorMessage: { value: null as string | null },
    startDefaultExport: vi.fn(),
    startExport: vi.fn(),
  },
  groupingShare: {
    isBusy: { value: false },
    statusLabel: { value: null as string | null },
    errorMessage: { value: null as string | null },
    revokingShareId: { value: null as string | null },
    shares: { value: [] as unknown[] },
    startShare: vi.fn(),
    copyShareLink: vi.fn(),
    revokePublicShare: vi.fn(),
  },
  seatingShare: {
    isBusy: { value: false },
    statusLabel: { value: null as string | null },
    errorMessage: { value: null as string | null },
    revokingShareId: { value: null as string | null },
    shares: { value: [] as unknown[] },
    startShare: vi.fn(),
    copyShareLink: vi.fn(),
    revokePublicShare: vi.fn(),
  },
}));

const guestOverviewMocks = vi.hoisted(() => ({
  availableRosters: { value: [] as unknown[] },
  availableTemplates: { value: [] as unknown[] },
  selectedRosterId: { value: null as string | null },
  selectedTemplateId: { value: null as string | null },
  currentScreen: { value: "class-workspace" as "class-workspace" | "planner" },
  plannerInitialView: { value: "groups" as "groups" | "seats" | "rules" },
  isBootstrapping: { value: false },
  bootstrapError: { value: null as string | null },
  plannerActionError: { value: null as string | null },
  guestAuthoringClosed: { value: false },
  classWorkspaceSummary: { value: null as unknown },
  currentSnapshotId: { value: null as string | null },
  overviewCapabilities: {
    show_grouping_option: true,
    show_seating_option: true,
    show_rules_option: true,
    show_roster_actions: true,
    show_template_actions: true,
  },
  guestPlannerState: {
    draft: { value: null as unknown },
    roster: { value: null as unknown },
    template: { value: null as unknown },
  },
  isRosterModalOpen: { value: false },
  isTemplateModalOpen: { value: false },
  activeRosterModal: { value: null as unknown },
  activeTemplateModal: { value: null as unknown },
  overviewDeleteRosterTarget: { value: null as unknown },
  overviewDeleteTemplateTarget: { value: null as unknown },
  overviewDeleteRosterError: { value: null as string | null },
  overviewDeleteTemplateError: { value: null as string | null },
  isDeletingOverviewRoster: { value: false },
  isDeletingOverviewTemplate: { value: false },
  rosterImportPreviewApiPath:
    "/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview",
  selectWorkspaceRoster: vi.fn(),
  selectWorkspaceTemplate: vi.fn(),
  bootstrapGuestWorkspace: vi.fn(),
  openGroupingWorkspace: vi.fn(),
  openSeatingWorkspace: vi.fn(),
  changeGroupingRoster: vi.fn(),
  changeGroupingTemplate: vi.fn(),
  changeSeatingTemplate: vi.fn(),
  startNewGroupingDraft: vi.fn(),
  startNewSeatingDraft: vi.fn(),
  openRulesWorkspace: vi.fn(),
  prepareOverviewDistributionScope: vi.fn(),
  selectPlannerWorkspaceMode: vi.fn(),
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

// eslint-disable-next-line vue/one-component-per-file
const PlannerClassWorkspaceStub = defineComponent({
  name: "PlannerClassWorkspace",
  props: {
    overviewCapabilities: { type: Object, required: false, default: null },
    groupingExportBusy: { type: Boolean, required: false, default: false },
    groupingExportErrorMessage: { type: String, required: false, default: null },
    groupingShareBusy: { type: Boolean, required: false, default: false },
    groupingShareStatusLabel: { type: String, required: false, default: null },
    groupingShareErrorMessage: { type: String, required: false, default: null },
    groupingShareRevokingId: { type: String, required: false, default: null },
    groupingShares: { type: Array, required: false, default: () => [] },
    seatingExportBusy: { type: Boolean, required: false, default: false },
    seatingExportErrorMessage: { type: String, required: false, default: null },
    seatingShareBusy: { type: Boolean, required: false, default: false },
    seatingShareStatusLabel: { type: String, required: false, default: null },
    seatingShareErrorMessage: { type: String, required: false, default: null },
    seatingShareRevokingId: { type: String, required: false, default: null },
    seatingShares: { type: Array, required: false, default: () => [] },
  },
  template: "<div data-test='planner-class-workspace-stub' />",
});

// eslint-disable-next-line vue/one-component-per-file
const ClassroomPlannerGuestWorkspaceShellStub = defineComponent({
  name: "ClassroomPlannerGuestWorkspaceShell",
  template: "<div data-test='guest-planner-shell-stub' />",
});

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

vi.mock("./usePublicGroupingExportFlow", () => ({
  usePublicGroupingExportFlow: () => publicFlowMocks.groupingExport,
}));

vi.mock("./usePublicSeatingExportFlow", () => ({
  usePublicSeatingExportFlow: () => publicFlowMocks.seatingExport,
}));

vi.mock("./usePublicGroupingShareFlow", () => ({
  usePublicGroupingShareFlow: () => publicFlowMocks.groupingShare,
}));

vi.mock("./usePublicSeatingShareFlow", () => ({
  usePublicSeatingShareFlow: () => publicFlowMocks.seatingShare,
}));

function mountView() {
  const pinia = createPinia();
  setActivePinia(pinia);
  return mount(ClassroomPlannerGuestOverviewView, {
    global: {
      plugins: [pinia],
      stubs: {
        PlannerClassWorkspace: PlannerClassWorkspaceStub,
        ClassroomPlannerGuestWorkspaceShell: ClassroomPlannerGuestWorkspaceShellStub,
        CreateRosterModal: true,
        CreateRoomTemplateModal: true,
        PlannerConfirmationDialog: true,
      },
    },
  });
}

describe("ClassroomPlannerGuestOverviewView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    routerMocks.push.mockReset();
    guestOverviewMocks.currentScreen.value = "class-workspace";
    guestOverviewMocks.plannerInitialView.value = "groups";
    guestOverviewMocks.isBootstrapping.value = false;
    guestOverviewMocks.bootstrapError.value = null;
    guestOverviewMocks.plannerActionError.value = null;
    guestOverviewMocks.guestAuthoringClosed.value = false;
    guestOverviewMocks.classWorkspaceSummary.value = null;
    guestOverviewMocks.openGroupingWorkspace.mockReset();
    guestOverviewMocks.openSeatingWorkspace.mockReset();
    guestOverviewMocks.openRulesWorkspace.mockReset();
    guestOverviewMocks.prepareOverviewDistributionScope.mockReset();
    guestOverviewMocks.prepareOverviewDistributionScope.mockResolvedValue(true);
    guestOverviewMocks.selectPlannerWorkspaceMode.mockReset();
    publicFlowMocks.groupingExport.isBusy.value = false;
    publicFlowMocks.groupingExport.errorMessage.value = null;
    publicFlowMocks.groupingExport.startDefaultExport.mockReset();
    publicFlowMocks.groupingExport.startExport.mockReset();
    publicFlowMocks.seatingExport.isBusy.value = false;
    publicFlowMocks.seatingExport.errorMessage.value = null;
    publicFlowMocks.seatingExport.startDefaultExport.mockReset();
    publicFlowMocks.seatingExport.startExport.mockReset();
    publicFlowMocks.groupingShare.isBusy.value = false;
    publicFlowMocks.groupingShare.statusLabel.value = null;
    publicFlowMocks.groupingShare.errorMessage.value = null;
    publicFlowMocks.groupingShare.revokingShareId.value = null;
    publicFlowMocks.groupingShare.shares.value = [];
    publicFlowMocks.groupingShare.startShare.mockReset();
    publicFlowMocks.groupingShare.copyShareLink.mockReset();
    publicFlowMocks.groupingShare.revokePublicShare.mockReset();
    publicFlowMocks.seatingShare.isBusy.value = false;
    publicFlowMocks.seatingShare.statusLabel.value = null;
    publicFlowMocks.seatingShare.errorMessage.value = null;
    publicFlowMocks.seatingShare.revokingShareId.value = null;
    publicFlowMocks.seatingShare.shares.value = [];
    publicFlowMocks.seatingShare.startShare.mockReset();
    publicFlowMocks.seatingShare.copyShareLink.mockReset();
    publicFlowMocks.seatingShare.revokePublicShare.mockReset();
  });

  it("keeps the final registration copy and passes checkpoint-3 capabilities to the class workspace", () => {
    const wrapper = mountView();
    const normalizedText = wrapper.text().replace(/\s+/g, " ").trim();

    expect(normalizedText).toContain(
      "Vissa funktioner kräver att du registrerar ett konto. Tryck här för att skapa ett.",
    );
    const classWorkspace = wrapper.findComponent(PlannerClassWorkspaceStub);
    expect(classWorkspace.exists()).toBe(true);
    expect(classWorkspace.props("overviewCapabilities")).toMatchObject({
      show_grouping_option: true,
      show_seating_option: true,
      show_rules_option: true,
    });
    expect(wrapper.find("[data-test='guest-planner-shell-stub']").exists()).toBe(false);
  });

  it("routes the class-workspace Regler affordance through the guest controller", async () => {
    const wrapper = mountView();

    wrapper.findComponent(PlannerClassWorkspaceStub).vm.$emit("open-rules");
    await nextTick();

    expect(guestOverviewMocks.openRulesWorkspace).toHaveBeenCalledTimes(1);
  });

  it("passes public share/export state into the guest class-workspace overview", () => {
    publicFlowMocks.groupingExport.isBusy.value = true;
    publicFlowMocks.groupingExport.errorMessage.value = "Grupp-export misslyckades.";
    publicFlowMocks.groupingShare.statusLabel.value = "Länk skapad.";
    publicFlowMocks.groupingShare.revokingShareId.value = "share-1";
    publicFlowMocks.groupingShare.shares.value = [shareArtifact];
    publicFlowMocks.seatingShare.errorMessage.value = "Sittplatslänk misslyckades.";

    const wrapper = mountView();
    const classWorkspace = wrapper.findComponent(PlannerClassWorkspaceStub);

    expect(classWorkspace.props("groupingExportBusy")).toBe(true);
    expect(classWorkspace.props("groupingExportErrorMessage")).toBe("Grupp-export misslyckades.");
    expect(classWorkspace.props("groupingShareStatusLabel")).toBe("Länk skapad.");
    expect(classWorkspace.props("groupingShareRevokingId")).toBe("share-1");
    expect(classWorkspace.props("groupingShares")).toEqual([shareArtifact]);
    expect(classWorkspace.props("seatingShareErrorMessage")).toBe("Sittplatslänk misslyckades.");
  });

  it("prepares overview drafts before starting public overview share and export operations", async () => {
    const wrapper = mountView();
    const classWorkspace = wrapper.findComponent(PlannerClassWorkspaceStub);

    classWorkspace.vm.$emit("prepare-overview-distribution", "grouping");
    classWorkspace.vm.$emit("export-overview-grouping-default");
    classWorkspace.vm.$emit("export-overview-grouping-option", "pdf_a4_portrait");
    classWorkspace.vm.$emit("share-overview-grouping-link");
    classWorkspace.vm.$emit("share-overview-seating-link");
    await flushPromises();

    expect(guestOverviewMocks.prepareOverviewDistributionScope).toHaveBeenCalledWith("grouping");
    expect(guestOverviewMocks.prepareOverviewDistributionScope).toHaveBeenCalledWith("seating");
    expect(publicFlowMocks.groupingExport.startDefaultExport).toHaveBeenCalledTimes(1);
    expect(publicFlowMocks.groupingExport.startExport).toHaveBeenCalledWith("pdf_a4_portrait");
    expect(publicFlowMocks.groupingShare.startShare).toHaveBeenCalledTimes(1);
    expect(publicFlowMocks.seatingShare.startShare).toHaveBeenCalledTimes(1);
  });

  it("does not start overview share/export operations when draft preparation is blocked", async () => {
    guestOverviewMocks.prepareOverviewDistributionScope.mockResolvedValue(false);
    const wrapper = mountView();
    const classWorkspace = wrapper.findComponent(PlannerClassWorkspaceStub);

    classWorkspace.vm.$emit("export-overview-grouping-default");
    classWorkspace.vm.$emit("share-overview-grouping-link");
    await flushPromises();

    expect(publicFlowMocks.groupingExport.startDefaultExport).not.toHaveBeenCalled();
    expect(publicFlowMocks.groupingShare.startShare).not.toHaveBeenCalled();
  });

  it("routes public overview copy and revoke events to the browser-owned share flow", async () => {
    const wrapper = mountView();
    const classWorkspace = wrapper.findComponent(PlannerClassWorkspaceStub);

    classWorkspace.vm.$emit("copy-overview-grouping-share", shareArtifact);
    classWorkspace.vm.$emit("revoke-overview-grouping-share", shareArtifact);
    classWorkspace.vm.$emit("copy-overview-seating-share", shareArtifact);
    classWorkspace.vm.$emit("revoke-overview-seating-share", shareArtifact);
    await nextTick();

    expect(publicFlowMocks.groupingShare.copyShareLink).toHaveBeenCalledWith(shareArtifact);
    expect(publicFlowMocks.groupingShare.revokePublicShare).toHaveBeenCalledWith(shareArtifact);
    expect(publicFlowMocks.seatingShare.copyShareLink).toHaveBeenCalledWith(shareArtifact);
    expect(publicFlowMocks.seatingShare.revokePublicShare).toHaveBeenCalledWith(shareArtifact);
  });

  it("renders the dedicated guest planner shell when the browser-owned draft is active", () => {
    guestOverviewMocks.currentScreen.value = "planner";

    const wrapper = mountView();

    expect(wrapper.find("[data-test='guest-planner-shell-stub']").exists()).toBe(true);
    expect(wrapper.find("[data-test='planner-class-workspace-stub']").exists()).toBe(false);
  });

  it("shows one login-first blocked state with the approved action targets when browser authoring is closed", () => {
    guestOverviewMocks.guestAuthoringClosed.value = true;

    const wrapper = mountView();
    const normalizedText = wrapper.text().replace(/\s+/g, " ").trim();

    expect(wrapper.find("[data-test='public-guest-authoring-closed-state']").exists()).toBe(true);
    expect(wrapper.find("[data-test='planner-class-workspace-stub']").exists()).toBe(false);
    expect(wrapper.find("[data-test='guest-planner-shell-stub']").exists()).toBe(false);
    expect(normalizedText).toContain("Logga in för att fortsätta");
    expect(normalizedText).toContain(
      "Klassrumskartan har redan använts inloggad i den här webbläsaren. Därför går det inte att skapa nya klasser eller klassrum här som gäst.",
    );
    expect(normalizedText).toContain(
      "Om du inte har ett konto ännu, eller om det här är någon annans webbläsare, kan du skapa ett nytt konto.",
    );
    expect(wrapper.get("[data-test='public-guest-authoring-closed-login']").attributes("href")).toBe(
      "https://api.hule.education/auth/login?app=skriptoteket&product_identity_realm=skriptoteket_standalone&return_to=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback&next=%2Fapps%2Fclassroom.group-seating-studio",
    );
    expect(wrapper.get("[data-test='public-guest-authoring-closed-login']").classes()).toContain(
      "public-guest-authoring-action",
    );
    expect(wrapper.get("[data-test='public-guest-authoring-closed-register']").attributes("href")).toBe(
      "https://api.hule.education/auth/register?app=skriptoteket&product_identity_realm=skriptoteket_standalone&return_to=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback&next=%2Fapps%2Fclassroom.group-seating-studio",
    );
    expect(wrapper.get("[data-test='public-guest-authoring-closed-register']").classes()).toContain(
      "public-guest-authoring-action",
    );
  });

  it("lets the blocked-state surface own the page even if a stale planner action error is still set", () => {
    guestOverviewMocks.guestAuthoringClosed.value = true;
    guestOverviewMocks.plannerActionError.value = "Stale error";

    const wrapper = mountView();

    expect(wrapper.find("[data-test='public-guest-authoring-closed-state']").exists()).toBe(true);
    expect(wrapper.text()).not.toContain("Stale error");
  });
});
