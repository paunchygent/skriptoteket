import { describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref, shallowRef } from "vue";

import { apiFetch } from "../../api/client";
import type { components } from "../../api/openapi";
import type { UiNotifier } from "../notify";
import { useEditorEditOps } from "./useEditorEditOps";

type EditorEditOpsResponse = components["schemas"]["EditorEditOpsResponse"];

vi.mock("../../api/client", () => ({
  apiFetch: vi.fn(),
  isApiError: (error: unknown) => error instanceof Error,
}));

function createNotify(): UiNotifier {
  return {
    info: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
    failure: vi.fn(),
  };
}

describe("useEditorEditOps", () => {
  it("applies and undoes a proposal", async () => {
    vi.useFakeTimers();
    const sourceCode = ref("print('hej')\n");
    const entrypoint = ref("run_tool\n");
    const settingsSchemaText = ref("[]");
    const inputSchemaText = ref("[]");
    const usageInstructions = ref("");

    const fingerprint = (text: string) => Promise.resolve(`sha256:${text}`);
    const baseFingerprints = {
      "tool.py": `sha256:${sourceCode.value}`,
      "entrypoint.txt": `sha256:${entrypoint.value}`,
      "settings_schema.json": `sha256:${settingsSchemaText.value}`,
      "input_schema.json": `sha256:${inputSchemaText.value}`,
      "usage_instructions.md": `sha256:${usageInstructions.value}`,
    };

    const response: EditorEditOpsResponse = {
      enabled: true,
      assistant_message: "Jag föreslår en enkel ändring.",
      base_fingerprints: baseFingerprints,
      ops: [
        {
          op: "replace",
          target_file: "tool.py",
          target: { kind: "document" },
          content: "print('hej')\nprint('klar')\n",
        },
      ],
    };

    vi.mocked(apiFetch).mockResolvedValueOnce(response);

    const createBeforeApplyCheckpoint = vi.fn();

    const scope = effectScope();
    const state = scope.run(() =>
      useEditorEditOps({
        toolId: ref("tool-1"),
        isReadOnly: ref(false),
        editorView: shallowRef(null),
        fields: {
          entrypoint,
          sourceCode,
          settingsSchemaText,
          inputSchemaText,
          usageInstructions,
        },
        createBeforeApplyCheckpoint,
        notify: createNotify(),
        fingerprint,
      }),
    );

    if (!state) {
      throw new Error("Failed to create editor edit ops state.");
    }

    await state.requestEditOps("Föreslå en ändring.");
    vi.runAllTimers();
    await nextTick();

    expect(state.proposal.value).not.toBeNull();

    const applied = await state.applyProposal();
    expect(applied).toBe(true);
    expect(createBeforeApplyCheckpoint).toHaveBeenCalled();
    expect(sourceCode.value).toContain("print('klar')");
    expect(state.hasUndoSnapshot.value).toBe(true);

    const undone = state.undoLastApply();
    expect(undone).toBe(true);
    expect(sourceCode.value).toBe("print('hej')\n");

    scope.stop();
    vi.useRealTimers();
  });

  it("disables undo when edits happen after apply", async () => {
    vi.useFakeTimers();
    const sourceCode = ref("print('hej')\n");
    const entrypoint = ref("run_tool\n");
    const settingsSchemaText = ref("[]");
    const inputSchemaText = ref("[]");
    const usageInstructions = ref("");

    const fingerprint = (text: string) => Promise.resolve(`sha256:${text}`);
    const baseFingerprints = {
      "tool.py": `sha256:${sourceCode.value}`,
      "entrypoint.txt": `sha256:${entrypoint.value}`,
      "settings_schema.json": `sha256:${settingsSchemaText.value}`,
      "input_schema.json": `sha256:${inputSchemaText.value}`,
      "usage_instructions.md": `sha256:${usageInstructions.value}`,
    };

    const response: EditorEditOpsResponse = {
      enabled: true,
      assistant_message: "Jag föreslår en enkel ändring.",
      base_fingerprints: baseFingerprints,
      ops: [
        {
          op: "replace",
          target_file: "tool.py",
          target: { kind: "document" },
          content: "print('hej')\nprint('klar')\n",
        },
      ],
    };

    vi.mocked(apiFetch).mockResolvedValueOnce(response);

    const scope = effectScope();
    const state = scope.run(() =>
      useEditorEditOps({
        toolId: ref("tool-1"),
        isReadOnly: ref(false),
        editorView: shallowRef(null),
        fields: {
          entrypoint,
          sourceCode,
          settingsSchemaText,
          inputSchemaText,
          usageInstructions,
        },
        createBeforeApplyCheckpoint: vi.fn(),
        notify: createNotify(),
        fingerprint,
      }),
    );

    if (!state) {
      throw new Error("Failed to create editor edit ops state.");
    }

    await state.requestEditOps("Föreslå en ändring.");
    vi.runAllTimers();
    await nextTick();

    await state.applyProposal();
    sourceCode.value = "print('ändrat')\n";
    await nextTick();

    expect(state.canUndo.value).toBe(false);

    scope.stop();
    vi.useRealTimers();
  });
});
