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
      bundleFiles: { "roster.py": "print('roster')" },
    });

    const scope = effectScope();
    const state = scope.run(() => useEditorCompareData(compareTarget, { workingCopyProvider: provider }));

    await flushPromises();

    expect(provider).toHaveBeenCalled();
    expect(state?.errorMessage.value).toBeNull();
    expect(state?.compareFiles.value?.["tool.py"]).toBe("print('hi')");
    expect(state?.compareBundleFiles.value).toEqual({ "roster.py": "print('roster')" });

    scope.stop();
  });

  it("loads bundle files when comparing a version", async () => {
    clientMocks.apiGet.mockResolvedValue({
      source_code: "print('hi')",
      entrypoint: "run_tool",
      bundle_files: { "roster.py": "print('roster')" },
    });

    const compareTarget = ref<EditorCompareTarget | null>({ kind: "version", versionId: "ver-1" });

    const scope = effectScope();
    const state = scope.run(() => useEditorCompareData(compareTarget));

    await flushPromises();

    expect(clientMocks.apiGet).toHaveBeenCalled();
    expect(state?.compareBundleFiles.value).toEqual({ "roster.py": "print('roster')" });

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
