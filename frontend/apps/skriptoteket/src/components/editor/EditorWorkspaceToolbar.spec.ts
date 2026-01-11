import { describe, expect, it } from "vitest";

import { mountWithContext } from "../../test/utils";
import EditorWorkspaceToolbar from "./EditorWorkspaceToolbar.vue";

describe("EditorWorkspaceToolbar", () => {
  it("shows save blockers when save is disabled", async () => {
    const wrapper = mountWithContext(EditorWorkspaceToolbar, {
      props: {
        isSaving: false,
        isReadOnly: false,
        hasDirtyChanges: false,
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
      },
    });

    await wrapper.find('button[aria-label="Spara/Öppna"]').trigger("click");

    expect(wrapper.text()).toContain("Blockerar sparning");
    expect(wrapper.text()).toContain("Indata (JSON): ogiltig");
  });
});
