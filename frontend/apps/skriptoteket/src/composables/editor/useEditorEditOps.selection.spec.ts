import { describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref, shallowRef } from "vue";

import { apiFetch } from "../../api/client";
import type { components } from "../../api/openapi";
import { useEditorEditOps } from "./useEditorEditOps";

type EditorEditOpsResponse = components["schemas"]["EditorEditOpsResponse"];

vi.mock("../../api/client", () => ({
  apiFetch: vi.fn(),
  isApiError: (error: unknown) => error instanceof Error,
}));

describe("useEditorEditOps (selection)", () => {
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
        allowRemoteFallback: ref(false),
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
        allowRemoteFallback: ref(false),
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
});
