import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref } from "vue";

import { useEditorCompareData, type WorkingCopyProvider } from "./useEditorCompareData";
import type { EditorCompareTarget } from "./useEditorCompareState";

const clientMocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  isApiError: vi.fn(),
}));

vi.mock("../../api/client", () => ({
  apiGet: clientMocks.apiGet,
  isApiError: clientMocks.isApiError,
}));

async function flushPromises(): Promise<void> {
  await nextTick();
  await Promise.resolve();
}

describe("useEditorCompareData", () => {
  beforeEach(() => {
    clientMocks.apiGet.mockReset();
    clientMocks.isApiError.mockReset();
  });

  it("loads local working copy when compare=working", async () => {
    const compareTarget = ref<EditorCompareTarget | null>({ kind: "working" });
    const provider: WorkingCopyProvider = vi.fn().mockResolvedValue({
      entrypoint: "run_tool",
      sourceCode: "print('hi')",
      settingsSchemaText: "[]",
      inputSchemaText: "[]",
      usageInstructions: "",
    });

    const scope = effectScope();
    const state = scope.run(() => useEditorCompareData(compareTarget, { workingCopyProvider: provider }));

    await flushPromises();

    expect(provider).toHaveBeenCalled();
    expect(state?.errorMessage.value).toBeNull();
    expect(state?.compareFiles.value?.["tool.py"]).toBe("print('hi')");

    scope.stop();
  });

  it("reports missing working copy when provider returns null", async () => {
    const compareTarget = ref<EditorCompareTarget | null>({ kind: "working" });
    const provider: WorkingCopyProvider = vi.fn().mockResolvedValue(null);

    const scope = effectScope();
    const state = scope.run(() => useEditorCompareData(compareTarget, { workingCopyProvider: provider }));

    await flushPromises();

    expect(provider).toHaveBeenCalled();
    expect(state?.compareFiles.value).toBeNull();
    expect(state?.errorMessage.value).toBeTruthy();

    scope.stop();
  });
});
