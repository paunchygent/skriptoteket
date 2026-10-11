import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { effectScope, nextTick, ref, type Ref } from "vue";

import type { UiNotifier } from "../notify";
import type { BundleFiles } from "./bundleFiles";
import type { EditorBaselineSnapshot, WorkingCopyHeadRecord } from "./editorPersistence";
import { useEditorWorkingCopy } from "./useEditorWorkingCopy";
import groupingPy from "../../../../../../src/skriptoteket/script_bank/scripts/gruppgenerator/grouping.py?raw";
import rosterPy from "../../../../../../src/skriptoteket/script_bank/scripts/gruppgenerator/roster.py?raw";

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

function createInitialSnapshot(
  overrides: Partial<EditorBaselineSnapshot> = {},
): EditorBaselineSnapshot {
  return {
    entrypoint: "run_tool",
    sourceCode: "print('hi')",
    bundleFiles: {},
    settingsSchemaText: "[]",
    inputSchemaText: "[]",
    usageInstructions: "",
    ...overrides,
  };
}

type EditorFieldRefs = {
  entrypoint: Ref<string>;
  sourceCode: Ref<string>;
  bundleFiles: Ref<BundleFiles>;
  settingsSchemaText: Ref<string>;
  inputSchemaText: Ref<string>;
  usageInstructions: Ref<string>;
};

function createFields(): EditorFieldRefs {
  return {
    entrypoint: ref("run_tool"),
    sourceCode: ref("print('hi')"),
    bundleFiles: ref<BundleFiles>({}),
    settingsSchemaText: ref("[]"),
    inputSchemaText: ref("[]"),
    usageInstructions: ref(""),
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

    const fields = createFields();
    const hasDirtyChanges = ref(true);
    const userId = ref("user-1");
    const toolId = ref("tool-1");
    const baseVersionId = ref("ver-1");
    const initialSnapshot = ref(createInitialSnapshot());

    const scope = effectScope();
    scope.run(() => {
      useEditorWorkingCopy({
        userId,
        toolId,
        baseVersionId,
        hasDirtyChanges,
        initialSnapshot,
        fields,
        notify: createNotify(),
      });
    });

    await flushPromises();

    fields.sourceCode.value = "print('bye')";
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

  it("autosaves the working copy head when only bundle files change, including later sibling edits", async () => {
    vi.useFakeTimers();

    const baselineBundle: BundleFiles = { "roster.py": rosterPy, "grouping.py": groupingPy };
    const fields = createFields();
    fields.bundleFiles.value = { ...baselineBundle };
    const hasDirtyChanges = ref(true);

    const scope = effectScope();
    scope.run(() => {
      useEditorWorkingCopy({
        userId: ref("user-1"),
        toolId: ref("tool-1"),
        baseVersionId: ref("ver-1"),
        hasDirtyChanges,
        initialSnapshot: ref(createInitialSnapshot({ bundleFiles: { ...baselineBundle } })),
        fields,
        notify: createNotify(),
      });
    });

    await flushPromises();

    const editedRoster = rosterPy + "\n# edit 1\n";
    fields.bundleFiles.value = { ...fields.bundleFiles.value, "roster.py": editedRoster };
    await nextTick();

    expect(persistenceMocks.saveWorkingCopyHead).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1300);
    await flushPromises();

    expect(persistenceMocks.saveWorkingCopyHead).toHaveBeenCalledTimes(1);
    expect(persistenceMocks.saveWorkingCopyHead.mock.calls[0]?.[0].fields).toEqual(
      expect.objectContaining({
        sourceCode: "print('hi')",
        bundleFiles: { "roster.py": editedRoster, "grouping.py": groupingPy },
      }),
    );

    const editedGrouping = groupingPy + "\n# edit 2\n";
    fields.bundleFiles.value = { ...fields.bundleFiles.value, "grouping.py": editedGrouping };
    await nextTick();

    vi.advanceTimersByTime(1300);
    await flushPromises();

    expect(persistenceMocks.saveWorkingCopyHead).toHaveBeenCalledTimes(2);
    expect(persistenceMocks.saveWorkingCopyHead.mock.calls[1]?.[0].fields).toEqual(
      expect.objectContaining({
        sourceCode: "print('hi')",
        bundleFiles: { "roster.py": editedRoster, "grouping.py": editedGrouping },
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
        initialSnapshot: ref(createInitialSnapshot()),
        fields: createFields(),
        notify: createNotify(),
      }),
    );

    await flushPromises();

    expect(workingCopyState?.isRestorePromptOpen.value).toBe(true);
    expect(workingCopyState?.hasRestoreCandidate.value).toBe(true);

    scope.stop();
  });

  it("stashes the restore candidate into local history when the user starts editing", async () => {
    persistenceMocks.getWorkingCopyHead.mockResolvedValue(
      createHeadRecord({ source_code: "print('changed')" }),
    );

    const notify = createNotify();
    const hasDirtyChanges = ref(false);

    const scope = effectScope();
    const workingCopyState = scope.run(() =>
      useEditorWorkingCopy({
        userId: ref("user-1"),
        toolId: ref("tool-1"),
        baseVersionId: ref("ver-1"),
        hasDirtyChanges,
        initialSnapshot: ref(createInitialSnapshot()),
        fields: createFields(),
        notify,
      }),
    );

    await flushPromises();

    expect(workingCopyState?.isRestorePromptOpen.value).toBe(true);

    hasDirtyChanges.value = true;
    for (let i = 0; i < 5; i += 1) {
      await flushPromises();
    }

    expect(persistenceMocks.createCheckpoint).toHaveBeenCalledWith(
      expect.objectContaining({
        userId: "user-1",
        toolId: "tool-1",
        kind: "auto",
        label: "Tidigare lokalt arbetsexemplar",
        fields: expect.objectContaining({
          sourceCode: "print('changed')",
        }),
      }),
    );
    expect(notify.success).toHaveBeenCalledWith("Tidigare lokalt arbetsexemplar sparat i lokal historik.");
    expect(workingCopyState?.isRestorePromptOpen.value).toBe(false);
    expect(workingCopyState?.hasRestoreCandidate.value).toBe(false);

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
        initialSnapshot: ref(createInitialSnapshot()),
        fields: createFields(),
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

  it("restores the baseline bundle files for a legacy head record without them", async () => {
    persistenceMocks.getWorkingCopyHead.mockResolvedValue(
      createHeadRecord({ source_code: "print('changed')" }),
    );

    const baselineBundleFiles: BundleFiles = {
      "roster.py": rosterPy,
      "grouping.py": groupingPy,
    };
    const fields = createFields();

    const scope = effectScope();
    const workingCopyState = scope.run(() =>
      useEditorWorkingCopy({
        userId: ref("user-1"),
        toolId: ref("tool-1"),
        baseVersionId: ref("ver-1"),
        hasDirtyChanges: ref(false),
        initialSnapshot: ref(createInitialSnapshot({ bundleFiles: baselineBundleFiles })),
        fields,
        notify: createNotify(),
      }),
    );

    await flushPromises();

    expect(workingCopyState?.isRestorePromptOpen.value).toBe(true);

    await workingCopyState?.restoreWorkingCopy();
    await flushPromises();

    expect(fields.bundleFiles.value).toEqual(baselineBundleFiles);
    expect(fields.bundleFiles.value).not.toBe(baselineBundleFiles);

    scope.stop();
  });

  it("warns only once if head save fails repeatedly", async () => {
    vi.useFakeTimers();
    persistenceMocks.saveWorkingCopyHead.mockRejectedValue(new Error("boom"));

    const notify = createNotify();

    const fields = createFields();
    const hasDirtyChanges = ref(true);

    const scope = effectScope();
    scope.run(() => {
      useEditorWorkingCopy({
        userId: ref("user-1"),
        toolId: ref("tool-1"),
        baseVersionId: ref("ver-1"),
        hasDirtyChanges,
        initialSnapshot: ref(createInitialSnapshot()),
        fields,
        notify,
      });
    });

    await flushPromises();

    fields.sourceCode.value = "print('bye')";
    await nextTick();
    vi.advanceTimersByTime(1300);
    await flushPromises();

    fields.sourceCode.value = "print('again')";
    await nextTick();
    vi.advanceTimersByTime(1300);
    await flushPromises();

    expect(notify.warning).toHaveBeenCalledTimes(1);
    expect(notify.warning).toHaveBeenCalledWith("Kunde inte spara arbetsexemplar lokalt.");

    scope.stop();
  });

  it("warns only once if auto checkpoints fail repeatedly", async () => {
    persistenceMocks.createCheckpoint.mockRejectedValue(new Error("boom"));

    const notify = createNotify();
    const scope = effectScope();
    const workingCopyState = scope.run(() =>
      useEditorWorkingCopy({
        userId: ref("user-1"),
        toolId: ref("tool-1"),
        baseVersionId: ref("ver-1"),
        hasDirtyChanges: ref(false),
        initialSnapshot: ref(createInitialSnapshot()),
        fields: createFields(),
        notify,
      }),
    );

    await flushPromises();

    await workingCopyState?.createAutoCheckpoint("Autosparad", { force: true });
    await workingCopyState?.createAutoCheckpoint("Autosparad", { force: true });

    expect(notify.warning).toHaveBeenCalledTimes(1);
    expect(notify.warning).toHaveBeenCalledWith("Kunde inte skapa automatisk återställningspunkt.");

    scope.stop();
  });
});
