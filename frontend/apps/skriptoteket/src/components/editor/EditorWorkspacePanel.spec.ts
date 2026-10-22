import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import type { DOMWrapper, VueWrapper } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { createTestRouter, mountWithContext } from "../../test/utils";
import ChatDrawer from "./ChatDrawer.vue";
import EditorWorkspaceDrawers from "./EditorWorkspaceDrawers.vue";
import EditorWorkspacePanel from "./EditorWorkspacePanel.vue";
import type { EditorWorkspacePanelProps } from "./EditorWorkspacePanel.types";

const BLOCKED_NOTE = "Daglig AI-gräns nådd.";

function buildProps(overrides: Partial<EditorWorkspacePanelProps> = {}): EditorWorkspacePanelProps {
  const editOpsState: EditorWorkspacePanelProps["editOpsState"] = {
    proposal: null,
    diffItems: [],
    previewMeta: null,
    previewErrorDetails: null,
    previewError: null,
    applyError: null,
    undoError: null,
    canApply: false,
    applyDisabledReason: null,
    aiStatus: null,
    aiAppliedAt: null,
    isApplying: false,
    requiresConfirmation: false,
    canUndo: false,
    undoDisabledReason: null,
    canRedo: false,
    redoDisabledReason: null,
    confirmationAccepted: false,
  };

  return {
    toolId: "tool-1",
    versions: [],
    selectedVersion: null,
    entrypointOptions: ["main.py"],
    changeSummary: "",
    entrypoint: "main.py",
    sourceCode: "print('hello')",
    bundleFiles: {},
    settingsSchemaText: "{}",
    inputSchemaText: "{}",
    settingsSchema: null,
    settingsSchemaError: null,
    inputSchema: [],
    inputSchemaError: null,
    schemaIssuesBySchema: { input_schema: [], settings_schema: [] },
    hasBlockingSchemaIssues: false,
    isSchemaValidating: false,
    schemaValidationError: null,
    validateSchemasNow: async () => true,
    usageInstructions: "",
    metadataTitle: "Tool",
    metadataSlug: "tool",
    metadataSummary: "",
    slugError: null,
    statusLine: "Publicerad",
    isTitleSaving: false,
    isSummarySaving: false,
    selectedProfessionIds: [],
    selectedCategoryIds: [],
    canEditTaxonomy: true,
    canEditMaintainers: true,
    canEditSlug: true,
    canRollbackVersions: false,
    isWorkflowSubmitting: false,
    isSaving: false,
    saveLabel: "Spara",
    saveTitle: "Spara",
    openCompareTitle: "",
    activeMode: "source",
    canEnterDiff: false,
    hasDirtyChanges: false,
    isReadOnly: false,
    isHistoryDrawerOpen: false,
    isChatDrawerOpen: false,
    isChatCollapsed: false,
    canCompareVersions: false,
    lockBadgeLabel: null,
    lockBadgeTone: "neutral",
    canSubmitReview: false,
    submitReviewTooltip: null,
    canPublish: false,
    canRequestChanges: false,
    canRollback: false,
    professions: [],
    categories: [],
    taxonomyError: null,
    isTaxonomyLoading: false,
    isSavingAllMetadata: false,
    maintainers: [],
    ownerUserId: null,
    isMaintainersLoading: false,
    isMaintainersSaving: false,
    maintainersError: null,
    compareTarget: null,
    compareActiveFileId: null,
    canCompareWorkingCopy: false,
    workingCopyProvider: null,
    localCheckpoints: [],
    pinnedCheckpointCount: 0,
    pinnedCheckpointLimit: 5,
    isCheckpointBusy: false,
    chatMessages: [],
    chatIsStreaming: false,
    chatError: null,
    aiBlockedNote: null,
    editOpsRequestError: null,
    editOpsDisabledMessage: null,
    editOpsClearDraftToken: 0,
    editOpsState,
    isEditOpsRequesting: false,
    isEditOpsSlow: false,
    ...overrides,
  };
}

function findNotes(wrapper: VueWrapper): DOMWrapper<Element>[] {
  return wrapper
    .findAll("p, small, span")
    .filter((node) => node.text().trim() === BLOCKED_NOTE);
}

function drawerStubs() {
  return {
    ScriptEditorHeaderPanel: true,
    EditorWorkspaceToolbar: true,
    WorkflowContextButtons: true,
    EditorWorkspaceModeSelector: true,
    EditorComparePanel: true,
    MetadataDrawer: true,
    InstructionsDrawer: true,
    MaintainersDrawer: true,
    EditorSandboxPanel: true,
    EditorSourceCodePanel: true,
    EditorInputSchemaPanel: true,
    EditorSettingsSchemaPanel: true,
    VersionHistoryDrawer: true,
  };
}

function mountPanelWithChatDrawer(overrides: Partial<EditorWorkspacePanelProps> = {}) {
  return mountWithContext(EditorWorkspacePanel, {
    props: buildProps({ isChatDrawerOpen: true, ...overrides }),
    global: {
      plugins: [createTestingPinia({ createSpy: vi.fn }), createTestRouter()],
      stubs: { ...drawerStubs(), EditorWorkspaceDrawers, ChatDrawer },
    },
  });
}

describe("EditorWorkspacePanel", () => {
  it("keys the main mode surface by the active editor mode", async () => {
    const wrapper = mount(EditorWorkspacePanel, {
      props: buildProps(),
      global: {
        stubs: {
          ScriptEditorHeaderPanel: true,
          EditorWorkspaceToolbar: true,
          WorkflowContextButtons: true,
          EditorWorkspaceModeSelector: true,
          EditorComparePanel: true,
          MetadataDrawer: true,
          InstructionsDrawer: true,
          MaintainersDrawer: true,
          EditorSandboxPanel: true,
          EditorSourceCodePanel: true,
          EditorInputSchemaPanel: true,
          EditorSettingsSchemaPanel: true,
          EditorWorkspaceDrawers: true,
          VersionHistoryDrawer: true,
        },
      },
    });

    expect(wrapper.find('[data-editor-mode="source"]').exists()).toBe(true);

    await wrapper.setProps(buildProps({ activeMode: "metadata" }));

    expect(wrapper.find('[data-editor-mode="metadata"]').exists()).toBe(true);
  });

  it("renders the AI blocked note and disables the composer textarea when aiBlockedNote is set", async () => {
    const wrapper = mountPanelWithChatDrawer({ aiBlockedNote: BLOCKED_NOTE });
    await nextTick();

    const notes = findNotes(wrapper);
    expect(notes.length).toBeGreaterThan(0);
    expect(notes.every((note) => note.text() === BLOCKED_NOTE)).toBe(true);

    const textarea = wrapper.get('textarea[aria-label="Meddelande till kodassistenten"]');
    expect(textarea.attributes("disabled")).toBeDefined();
    wrapper.unmount();
  });

  it("leaves the composer enabled and shows no AI note when aiBlockedNote is null", async () => {
    const wrapper = mountPanelWithChatDrawer({ aiBlockedNote: null });
    await nextTick();

    expect(findNotes(wrapper)).toHaveLength(0);
    const textarea = wrapper.get('textarea[aria-label="Meddelande till kodassistenten"]');
    expect(textarea.attributes("disabled")).toBeUndefined();
    wrapper.unmount();
  });
});
