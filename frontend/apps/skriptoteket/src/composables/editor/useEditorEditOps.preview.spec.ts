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

describe("useEditorEditOps (preview)", () => {
  it("requires confirmation before applying when preview requests it", async () => {
    vi.mocked(apiFetch).mockReset();

    const sourceCode = ref("print('hej')\n");
    const entrypoint = ref("run_tool\n");
    const settingsSchemaText = ref("[]");
    const inputSchemaText = ref("[]");
    const usageInstructions = ref("");

    const response: EditorEditOpsResponse = {
      enabled: true,
      assistant_message: "Jag föreslår en enkel ändring.",
      base_fingerprints: {
        "tool.py": `sha256:${sourceCode.value}`,
        "entrypoint.txt": `sha256:${entrypoint.value}`,
        "settings_schema.json": `sha256:${settingsSchemaText.value}`,
        "input_schema.json": `sha256:${inputSchemaText.value}`,
        "usage_instructions.md": `sha256:${usageInstructions.value}`,
      },
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
        requires_confirmation: true,
        fuzz_level_used: 1,
        max_offset: 0,
        normalizations_applied: [],
        applied_cleanly: false,
      },
    };

    vi.mocked(apiFetch).mockResolvedValueOnce(response).mockResolvedValueOnce(previewResponse);

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
    await nextTick();

    expect(state.canApply.value).toBe(false);
    expect(state.applyDisabledReason.value).toContain("Bekräfta");

    const appliedWithoutConfirmation = await state.applyProposal();
    expect(appliedWithoutConfirmation).toBe(false);
    expect(state.applyError.value).toContain("Bekräfta");

    state.setConfirmationAccepted(true);
    await nextTick();
    expect(state.canApply.value).toBe(true);

    scope.stop();
  });

  it("shows conflict errors and refreshes preview on 409", async () => {
    vi.mocked(apiFetch).mockReset();

    const sourceCode = ref("print('hej')\n");
    const entrypoint = ref("run_tool\n");
    const settingsSchemaText = ref("[]");
    const inputSchemaText = ref("[]");
    const usageInstructions = ref("");

    const response: EditorEditOpsResponse = {
      enabled: true,
      assistant_message: "Jag föreslår en enkel ändring.",
      base_fingerprints: {
        "tool.py": `sha256:${sourceCode.value}`,
        "entrypoint.txt": `sha256:${entrypoint.value}`,
        "settings_schema.json": `sha256:${settingsSchemaText.value}`,
        "input_schema.json": `sha256:${inputSchemaText.value}`,
        "usage_instructions.md": `sha256:${usageInstructions.value}`,
      },
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

    const conflictError = Object.assign(
      new Error(
        "Underlaget har ändrats sedan förhandsvisningen. Uppdatera förhandsvisningen och bekräfta igen.",
      ),
      { status: 409 },
    );

    vi.mocked(apiFetch)
      .mockResolvedValueOnce(response)
      .mockResolvedValueOnce(previewResponse)
      .mockRejectedValueOnce(conflictError)
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
    await nextTick();

    const applied = await state.applyProposal();
    expect(applied).toBe(false);
    expect(state.applyError.value).toBe(conflictError.message);
    expect(vi.mocked(apiFetch).mock.calls.length).toBe(4);

    scope.stop();
  });
});
