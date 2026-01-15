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

describe("useEditorEditOps (request)", () => {
  it("omits selection/cursor to force v2 semantics", async () => {
    vi.mocked(apiFetch).mockReset();

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

    const view = {
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
      | { cursor?: unknown; selection?: unknown }
      | undefined;

    expect(body).toBeTruthy();
    expect(body?.cursor).toBeUndefined();
    expect(body?.selection).toBeUndefined();

    scope.stop();
  });
});
