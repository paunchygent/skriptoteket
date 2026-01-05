import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { effectScope, nextTick, ref } from "vue";

import type { UiNotifier } from "../notify";
import { useEditorWorkingCopy } from "./useEditorWorkingCopy";
import type { WorkingCopyHeadRecord } from "./editorPersistence";

const persistenceMocks = vi.hoisted(() => ({
  getWorkingCopyHead: vi.fn(),
  saveWorkingCopyHead: vi.fn(),
  listCheckpoints: vi.fn(),
  createCheckpoint: vi.fn(),
  deleteCheckpoint: vi.fn(),
  trimAutoCheckpoints: vi.fn(),
  clearWorkingCopyData: vi.fn(),
}));

vi.mock("./editorPersistence", async () => {
  const actual = await vi.importActual<typeof import("./editorPersistence")>("./editorPersistence");
  return {
    ...actual,
    getWorkingCopyHead: persistenceMocks.getWorkingCopyHead,
    saveWorkingCopyHead: persistenceMocks.saveWorkingCopyHead,
    listCheckpoints: persistenceMocks.listCheckpoints,
    createCheckpoint: persistenceMocks.createCheckpoint,
    deleteCheckpoint: persistenceMocks.deleteCheckpoint,
    trimAutoCheckpoints: persistenceMocks.trimAutoCheckpoints,
    clearWorkingCopyData: persistenceMocks.clearWorkingCopyData,
  };
});

function createNotify(): UiNotifier {
  return {
    info: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
    failure: vi.fn(),
  };
}

function createHeadRecord(overrides: Partial<WorkingCopyHeadRecord> = {}): WorkingCopyHeadRecord {
  return {
    user_id: "user-1",
    tool_id: "tool-1",
    base_version_id: "ver-1",
    entrypoint: "run_tool",
    source_code: "print('hi')",
    settings_schema: "[]",
    input_schema: "[]",
    usage_instructions: "",
    updated_at: Date.now(),
    expires_at: Date.now() + 1000,
    ...overrides,
  };
}

async function flushPromises(): Promise<void> {
  await nextTick();
  await Promise.resolve();
}

describe("useEditorWorkingCopy", () => {
  beforeEach(() => {
    persistenceMocks.getWorkingCopyHead.mockResolvedValue(null);
    persistenceMocks.saveWorkingCopyHead.mockResolvedValue(createHeadRecord());
    persistenceMocks.listCheckpoints.mockResolvedValue([]);
    persistenceMocks.createCheckpoint.mockResolvedValue(null);
    persistenceMocks.deleteCheckpoint.mockResolvedValue(undefined);
    persistenceMocks.trimAutoCheckpoints.mockResolvedValue(undefined);
    persistenceMocks.clearWorkingCopyData.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("autosaves the working copy head when dirty changes occur", async () => {
    vi.useFakeTimers();

    const entrypoint = ref("run_tool");
    const sourceCode = ref("print('hi')");
    const settingsSchemaText = ref("[]");
    const inputSchemaText = ref("[]");
    const usageInstructions = ref("");
    const hasDirtyChanges = ref(true);
    const userId = ref("user-1");
    const toolId = ref("tool-1");
    const baseVersionId = ref("ver-1");
    const initialSnapshot = ref({
      entrypoint: "run_tool",
      sourceCode: "print('hi')",
      settingsSchemaText: "[]",
      inputSchemaText: "[]",
      usageInstructions: "",
    });

    const scope = effectScope();
    scope.run(() => {
      useEditorWorkingCopy({
        userId,
        toolId,
        baseVersionId,
        hasDirtyChanges,
        initialSnapshot,
        fields: {
          entrypoint,
          sourceCode,
          settingsSchemaText,
          inputSchemaText,
          usageInstructions,
        },
        notify: createNotify(),
      });
    });

    await flushPromises();

    sourceCode.value = "print('bye')";
    await nextTick();

    vi.advanceTimersByTime(1300);
    await flushPromises();

    expect(persistenceMocks.saveWorkingCopyHead).toHaveBeenCalledWith(
      expect.objectContaining({
        userId: "user-1",
        toolId: "tool-1",
        baseVersionId: "ver-1",
        fields: expect.objectContaining({ sourceCode: "print('bye')" }),
      }),
    );

    scope.stop();
  });

  it("shows a restore prompt when a working copy differs from the baseline", async () => {
    persistenceMocks.getWorkingCopyHead.mockResolvedValue(
      createHeadRecord({ source_code: "print('changed')" }),
    );

    const scope = effectScope();
    const hasDirtyChanges = ref(false);
    const workingCopyState = scope.run(() =>
      useEditorWorkingCopy({
        userId: ref("user-1"),
        toolId: ref("tool-1"),
        baseVersionId: ref("ver-1"),
        hasDirtyChanges,
        initialSnapshot: ref({
          entrypoint: "run_tool",
          sourceCode: "print('hi')",
          settingsSchemaText: "[]",
          inputSchemaText: "[]",
          usageInstructions: "",
        }),
        fields: {
          entrypoint: ref("run_tool"),
          sourceCode: ref("print('hi')"),
          settingsSchemaText: ref("[]"),
          inputSchemaText: ref("[]"),
          usageInstructions: ref(""),
        },
        notify: createNotify(),
      }),
    );

    await flushPromises();

    expect(workingCopyState?.isRestorePromptOpen.value).toBe(true);
    expect(workingCopyState?.hasRestoreCandidate.value).toBe(true);

    scope.stop();
  });

  it("clears local data when discarding the working copy", async () => {
    const scope = effectScope();
    const workingCopyState = scope.run(() =>
      useEditorWorkingCopy({
        userId: ref("user-1"),
        toolId: ref("tool-1"),
        baseVersionId: ref("ver-1"),
        hasDirtyChanges: ref(false),
        initialSnapshot: ref({
          entrypoint: "run_tool",
          sourceCode: "print('hi')",
          settingsSchemaText: "[]",
          inputSchemaText: "[]",
          usageInstructions: "",
        }),
        fields: {
          entrypoint: ref("run_tool"),
          sourceCode: ref("print('hi')"),
          settingsSchemaText: ref("[]"),
          inputSchemaText: ref("[]"),
          usageInstructions: ref(""),
        },
        notify: createNotify(),
      }),
    );

    await flushPromises();

    await workingCopyState?.discardWorkingCopy();

    expect(persistenceMocks.clearWorkingCopyData).toHaveBeenCalledWith({
      userId: "user-1",
      toolId: "tool-1",
    });

    scope.stop();
  });
});
