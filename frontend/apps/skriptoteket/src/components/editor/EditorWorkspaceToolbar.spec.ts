import { describe, expect, it } from "vitest";

import { mountWithContext } from "../../test/utils";
import EditorWorkspaceToolbar from "./EditorWorkspaceToolbar.vue";

const baseProps = {
  toolId: "tool-1",
  toolTitle: "Verktyg 1",
  toolSlug: "verktyg-1",
  canCreateTool: true,
};

describe("EditorWorkspaceToolbar", () => {
  it("shows save blockers when save is disabled", async () => {
    const wrapper = mountWithContext(EditorWorkspaceToolbar, {
      props: {
        ...baseProps,
        isSaving: false,
        isReadOnly: false,
        hasDirtyChanges: false,
        isChatCollapsed: true,
        saveLabel: "Spara arbetsversion",
        saveTitle: "",
        changeSummary: "",
        inputSchemaError: "Ogiltig JSON",
        settingsSchemaError: null,
        hasBlockingSchemaIssues: false,
        isCheckpointBusy: false,
        lockBadgeLabel: null,
        lockBadgeTone: "neutral",
        aiStatus: null,
        aiAppliedAt: null,
        aiCanUndo: false,
        aiUndoDisabledReason: null,
        aiCanRedo: false,
        aiRedoDisabledReason: null,
        aiError: null,
      },
    });

    const saveButton = wrapper.findAll("button").find((button) => button.text().includes("Spara/Öppna"));
    expect(saveButton).toBeDefined();
    await saveButton!.trigger("click");

    expect(wrapper.text()).toContain("Blockerar sparning");
    expect(wrapper.text()).toContain("Indata (JSON): ogiltig");
  });

  it("shows AI errors in the AI popover", async () => {
    const wrapper = mountWithContext(EditorWorkspaceToolbar, {
      props: {
        ...baseProps,
        isSaving: false,
        isReadOnly: false,
        hasDirtyChanges: false,
        isChatCollapsed: false,
        saveLabel: "Spara arbetsversion",
        saveTitle: "",
        changeSummary: "",
        inputSchemaError: null,
        settingsSchemaError: null,
        hasBlockingSchemaIssues: false,
        isCheckpointBusy: false,
        lockBadgeLabel: null,
        lockBadgeTone: "neutral",
        aiStatus: "applied",
        aiAppliedAt: new Date().toISOString(),
        aiCanUndo: true,
        aiUndoDisabledReason: null,
        aiCanRedo: false,
        aiRedoDisabledReason: "Ingen AI-ändring att återställa.",
        aiError: "Det gick inte att ångra.",
      },
    });

    await wrapper.find('button[aria-label="AI-ändring"]').trigger("click");

    expect(wrapper.text()).toContain("Det gick inte att ångra.");
  });

  it("uses canonical icon buttons for AI undo and redo", () => {
    const wrapper = mountWithContext(EditorWorkspaceToolbar, {
      props: {
        ...baseProps,
        isSaving: false,
        isReadOnly: false,
        hasDirtyChanges: false,
        isChatCollapsed: false,
        saveLabel: "Spara arbetsversion",
        saveTitle: "",
        changeSummary: "",
        inputSchemaError: null,
        settingsSchemaError: null,
        hasBlockingSchemaIssues: false,
        isCheckpointBusy: false,
        lockBadgeLabel: null,
        lockBadgeTone: "neutral",
        aiStatus: "applied",
        aiAppliedAt: new Date().toISOString(),
        aiCanUndo: true,
        aiUndoDisabledReason: null,
        aiCanRedo: true,
        aiRedoDisabledReason: null,
        aiError: null,
      },
    });

    expect(wrapper.find('button[aria-label="Ångra AI-ändring"]').exists()).toBe(true);
    expect(wrapper.find('button[aria-label="Återställ AI-ändring"]').exists()).toBe(true);
    expect(wrapper.text()).not.toContain("↶");
    expect(wrapper.text()).not.toContain("↷");
  });

  it("renders dirty and lock states through the shared dense status pill", () => {
    const wrapper = mountWithContext(EditorWorkspaceToolbar, {
      props: {
        ...baseProps,
        isSaving: false,
        isReadOnly: false,
        hasDirtyChanges: true,
        isChatCollapsed: false,
        saveLabel: "Spara arbetsversion",
        saveTitle: "",
        changeSummary: "",
        inputSchemaError: null,
        settingsSchemaError: null,
        hasBlockingSchemaIssues: false,
        isCheckpointBusy: false,
        lockBadgeLabel: "Låst av dig",
        lockBadgeTone: "success",
        aiStatus: null,
        aiAppliedAt: null,
        aiCanUndo: false,
        aiUndoDisabledReason: null,
        aiCanRedo: false,
        aiRedoDisabledReason: null,
        aiError: null,
      },
    });

    const pills = wrapper.findAll('[data-ui="dense-status-pill"]');

    expect(pills).toHaveLength(2);
    expect(pills[0].text()).toContain("Osparat");
    expect(pills[1].text()).toContain("Låst av dig");
  });
});
