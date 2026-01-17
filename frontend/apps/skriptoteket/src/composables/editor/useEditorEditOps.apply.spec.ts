import { describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref, shallowRef } from "vue";

import { apiFetch } from "../../api/client";
import type { components } from "../../api/openapi";
import { useEditorEditOps } from "./useEditorEditOps";

type EditorEditOpsResponse = components["schemas"]["EditorEditOpsResponse"];
type EditorEditOpsPreviewResponse = components["schemas"]["EditorEditOpsPreviewResponse"];

vi.mock("../../api/client", () => ({
  apiFetch: vi.fn(),
  isApiError: (error: unknown) => error instanceof Error,
}));

vi.mock("../../api/correlation", () => ({
  createCorrelationId: () => "corr-1",
}));

describe("useEditorEditOps (apply)", () => {
  it("applies, undoes, and redoes a proposal", async () => {
    vi.useFakeTimers();
    const sourceCode = ref("print('hej')\n");
    const entrypoint = ref("run_tool\n");
    const settingsSchemaText = ref("[]");
    const inputSchemaText = ref("[]");
    const usageInstructions = ref("");

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
          op: "patch",
          target_file: "tool.py",
          patch_lines: [
            "@@ -1,1 +1,2 @@",
            "-print('hej')",
            "+print('hej')",
            "+print('klar')",
          ],
        },
      ],
    };

    const previewResponse: EditorEditOpsPreviewResponse = {
      ok: true,
      after_virtual_files: {
        "tool.py": "print('hej')\nprint('klar')\n",
        "entrypoint.txt": entrypoint.value,
        "settings_schema.json": settingsSchemaText.value,
        "input_schema.json": inputSchemaText.value,
        "usage_instructions.md": usageInstructions.value,
      },
      errors: [],
      error_details: [],
      meta: {
        base_hash: "sha256:base",
        patch_id: "sha256:patch",
        requires_confirmation: false,
        fuzz_level_used: 0,
        max_offset: 0,
        normalizations_applied: [],
        applied_cleanly: true,
      },
    };

    vi.mocked(apiFetch)
      .mockResolvedValueOnce(response)
      .mockResolvedValueOnce(previewResponse)
      .mockResolvedValueOnce(previewResponse);

    const createBeforeApplyCheckpoint = vi.fn();

    const scope = effectScope();
    const state = scope.run(() =>
      useEditorEditOps({
        toolId: ref("tool-1"),
        allowRemoteFallback: ref(false),
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
      }),
    );

    if (!state) {
      throw new Error("Failed to create editor edit ops state.");
    }

    await state.requestEditOps("Föreslå en ändring.");
    vi.runAllTimers();
    await nextTick();

    expect(state.proposal.value).not.toBeNull();
    expect(vi.mocked(apiFetch).mock.calls[0]?.[1]?.headers).toEqual({ "X-Correlation-ID": "corr-1" });
    expect(vi.mocked(apiFetch).mock.calls[1]?.[1]?.headers).toEqual({ "X-Correlation-ID": "corr-1" });

    const applied = await state.applyProposal();
    expect(applied).toBe(true);
    expect(vi.mocked(apiFetch).mock.calls[2]?.[1]?.headers).toEqual({ "X-Correlation-ID": "corr-1" });
    expect(createBeforeApplyCheckpoint).toHaveBeenCalled();
    expect(sourceCode.value).toContain("print('klar')");
    expect(state.panelState.value.aiStatus).toBe("applied");

    const undone = state.undoLastApply();
    expect(undone).toBe(true);
    expect(sourceCode.value).toBe("print('hej')\n");
    expect(state.panelState.value.aiStatus).toBe("undone");
    expect(state.canRedo.value).toBe(true);

    const redone = state.redoLastApply();
    expect(redone).toBe(true);
    expect(sourceCode.value).toContain("print('klar')");
    expect(state.panelState.value.aiStatus).toBe("applied");

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
          op: "patch",
          target_file: "tool.py",
          patch_lines: [
            "@@ -1,1 +1,2 @@",
            "-print('hej')",
            "+print('hej')",
            "+print('klar')",
          ],
        },
      ],
    };

    const previewResponse: EditorEditOpsPreviewResponse = {
      ok: true,
      after_virtual_files: {
        "tool.py": "print('hej')\nprint('klar')\n",
        "entrypoint.txt": entrypoint.value,
        "settings_schema.json": settingsSchemaText.value,
        "input_schema.json": inputSchemaText.value,
        "usage_instructions.md": usageInstructions.value,
      },
      errors: [],
      error_details: [],
      meta: {
        base_hash: "sha256:base",
        patch_id: "sha256:patch",
        requires_confirmation: false,
        fuzz_level_used: 0,
        max_offset: 0,
        normalizations_applied: [],
        applied_cleanly: true,
      },
    };

    vi.mocked(apiFetch)
      .mockResolvedValueOnce(response)
      .mockResolvedValueOnce(previewResponse)
      .mockResolvedValueOnce(previewResponse);

    const scope = effectScope();
    const state = scope.run(() =>
      useEditorEditOps({
        toolId: ref("tool-1"),
        allowRemoteFallback: ref(false),
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
