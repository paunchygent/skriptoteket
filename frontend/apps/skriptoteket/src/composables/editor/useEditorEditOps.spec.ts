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

describe("useEditorEditOps", () => {
  it("applies and undoes a proposal", async () => {
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
          op: "replace",
          target_file: "tool.py",
          target: { kind: "document" },
          content: "print('hej')\nprint('klar')\n",
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

  it("omits cursor unless explicitly targeted recently", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-10T12:00:00Z"));

    const sourceCode = ref("print('hej')\n");
    const entrypoint = ref("run_tool\n");
    const settingsSchemaText = ref("[]");
    const inputSchemaText = ref("[]");
    const usageInstructions = ref("");

    const baseFingerprints = {
      "tool.py": "sha256:tool",
      "entrypoint.txt": "sha256:entrypoint",
      "settings_schema.json": "sha256:settings",
      "input_schema.json": "sha256:input",
      "usage_instructions.md": "sha256:usage",
    };

    const response: EditorEditOpsResponse = {
      enabled: false,
      assistant_message: "disabled",
      base_fingerprints: baseFingerprints,
      ops: [],
    };

    vi.mocked(apiFetch).mockResolvedValue(response);

    const listeners: Record<string, ((event: Event) => void) | undefined> = {};
    const view = {
      dom: {
        addEventListener: (name: string, cb: (event: Event) => void) => {
          listeners[name] = cb;
        },
        removeEventListener: (name: string) => {
          listeners[name] = undefined;
        },
      },
      state: {
        selection: {
          main: { empty: true, from: 5, to: 5, head: 5 },
        },
      },
    } as unknown as import("@codemirror/view").EditorView;

    const scope = effectScope();
    const state = scope.run(() =>
      useEditorEditOps({
        toolId: ref("tool-1"),
        isReadOnly: ref(false),
        editorView: shallowRef(view),
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

    await nextTick();

    await state.requestEditOps("Test 1");
    const firstBody = vi.mocked(apiFetch).mock.calls[0]?.[1]?.body as
      | { cursor?: unknown; selection?: unknown }
      | undefined;
    expect(firstBody).toBeTruthy();
    expect(firstBody?.cursor).toBeUndefined();
    expect(firstBody?.selection).toBeUndefined();

    vi.mocked(apiFetch).mockClear();
    listeners.pointerdown?.(new Event("pointerdown"));

    await state.requestEditOps("Test 2");
    const secondBody = vi.mocked(apiFetch).mock.calls[0]?.[1]?.body as
      | { cursor?: unknown; selection?: unknown }
      | undefined;
    expect(secondBody).toBeTruthy();
    expect(secondBody?.cursor).toEqual({ pos: 5 });

    scope.stop();
    vi.useRealTimers();
  });

  it("includes cursor at selection end when selection exists", async () => {
    vi.mocked(apiFetch).mockReset();
    vi.useFakeTimers();

    const sourceCode = ref("print('hej')\n");
    const entrypoint = ref("run_tool\n");
    const settingsSchemaText = ref("[]");
    const inputSchemaText = ref("[]");
    const usageInstructions = ref("");

    const response: EditorEditOpsResponse = {
      enabled: false,
      assistant_message: "disabled",
      base_fingerprints: {
        "tool.py": "sha256:tool",
        "entrypoint.txt": "sha256:entrypoint",
        "settings_schema.json": "sha256:settings",
        "input_schema.json": "sha256:input",
        "usage_instructions.md": "sha256:usage",
      },
      ops: [],
    };

    vi.mocked(apiFetch).mockResolvedValue(response);

    const listeners: Record<string, ((event: Event) => void) | undefined> = {};
    const view = {
      dom: {
        addEventListener: (name: string, cb: (event: Event) => void) => {
          listeners[name] = cb;
        },
        removeEventListener: (name: string) => {
          listeners[name] = undefined;
        },
      },
      state: {
        selection: {
          main: { empty: false, from: 2, to: 7, head: 2 },
        },
      },
    } as unknown as import("@codemirror/view").EditorView;

    const scope = effectScope();
    const state = scope.run(() =>
      useEditorEditOps({
        toolId: ref("tool-1"),
        isReadOnly: ref(false),
        editorView: shallowRef(view),
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

    await nextTick();

    await state.requestEditOps("Test");

    const body = vi.mocked(apiFetch).mock.calls[0]?.[1]?.body as
      | { cursor?: { pos: number }; selection?: { from: number; to: number } }
      | undefined;

    expect(body).toBeTruthy();
    expect(body?.selection).toEqual({ from: 2, to: 7 });
    expect(body?.cursor).toEqual({ pos: 7 });

    scope.stop();
    vi.useRealTimers();
  });

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
          op: "replace",
          target_file: "tool.py",
          target: { kind: "document" },
          content: "print('hej')\nprint('klar')\n",
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
          op: "replace",
          target_file: "tool.py",
          target: { kind: "document" },
          content: "print('hej')\nprint('klar')\n",
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
