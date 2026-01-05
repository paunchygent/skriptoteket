import { computed, onScopeDispose, ref, watch, type Ref } from "vue";

import type { UiNotifier } from "../notify";
import {
  AUTO_CHECKPOINT_CAP,
  AUTO_CHECKPOINT_TTL_DAYS,
  PINNED_CHECKPOINT_CAP,
  clearWorkingCopyData,
  checkpointFieldsFromRecord,
  createCheckpoint,
  deleteCheckpoint,
  getWorkingCopyHead,
  listCheckpoints,
  saveWorkingCopyHead,
  trimAutoCheckpoints,
  workingCopyFieldsFromRecord,
  type CheckpointKind,
  type CheckpointRecord,
  type EditorWorkingCopyFields,
  type WorkingCopyHeadRecord,
} from "./editorPersistence";
import { VIRTUAL_FILE_IDS, virtualFileTextFromEditorFields } from "./virtualFiles";

export type EditorWorkingCopyCheckpointSummary = {
  id: string;
  kind: CheckpointKind;
  label: string;
  createdAt: number;
};

export type EditorBaselineSnapshot = {
  entrypoint: string;
  sourceCode: string;
  settingsSchemaText: string;
  inputSchemaText: string;
  usageInstructions: string;
};

type UseEditorWorkingCopyOptions = {
  userId: Readonly<Ref<string | null>>;
  toolId: Readonly<Ref<string>>;
  baseVersionId: Readonly<Ref<string | null>>;
  hasDirtyChanges: Readonly<Ref<boolean>>;
  initialSnapshot: Readonly<Ref<EditorBaselineSnapshot | null>>;
  fields: {
    entrypoint: Ref<string>;
    sourceCode: Ref<string>;
    settingsSchemaText: Ref<string>;
    inputSchemaText: Ref<string>;
    usageInstructions: Ref<string>;
  };
  notify: UiNotifier;
};

const HEAD_SAVE_DEBOUNCE_MS = 1200;
const AUTO_CHECKPOINT_INTERVAL_MS = 60_000;

function fieldsFingerprint(fields: EditorWorkingCopyFields): string {
  return [
    fields.entrypoint,
    fields.sourceCode,
    fields.settingsSchemaText,
    fields.inputSchemaText,
    fields.usageInstructions,
  ].join("\u0000");
}

function areFieldsEqual(a: EditorWorkingCopyFields, b: EditorWorkingCopyFields): boolean {
  return fieldsFingerprint(a) === fieldsFingerprint(b);
}

export function useEditorWorkingCopy(options: UseEditorWorkingCopyOptions) {
  const {
    userId,
    toolId,
    baseVersionId,
    hasDirtyChanges,
    initialSnapshot,
    fields,
    notify,
  } = options;

  const workingCopyHead = ref<WorkingCopyHeadRecord | null>(null);
  const restoreCandidate = ref<WorkingCopyHeadRecord | null>(null);
  const isRestorePromptOpen = ref(false);
  const isLoading = ref(false);

  const checkpoints = ref<CheckpointRecord[]>([]);
  const isCheckpointBusy = ref(false);

  let headSaveTimer: ReturnType<typeof setTimeout> | null = null;
  let autoCheckpointTimer: ReturnType<typeof setInterval> | null = null;
  let lastAutoCheckpointFingerprint = "";
  let hasWarnedHeadSaveFailure = false;
  let hasWarnedCheckpointFailure = false;

  const canPersist = computed(() => Boolean(userId.value) && Boolean(toolId.value));

  const currentFields = computed<EditorWorkingCopyFields>(() => ({
    entrypoint: fields.entrypoint.value,
    sourceCode: fields.sourceCode.value,
    settingsSchemaText: fields.settingsSchemaText.value,
    inputSchemaText: fields.inputSchemaText.value,
    usageInstructions: fields.usageInstructions.value,
  }));

  const baselineFields = computed<EditorWorkingCopyFields | null>(() => {
    const snapshot = initialSnapshot.value;
    if (!snapshot) return null;
    return {
      entrypoint: snapshot.entrypoint,
      sourceCode: snapshot.sourceCode,
      settingsSchemaText: snapshot.settingsSchemaText,
      inputSchemaText: snapshot.inputSchemaText,
      usageInstructions: snapshot.usageInstructions,
    };
  });

  const hasRestoreCandidate = computed(() => restoreCandidate.value !== null);

  const restoreDiffItems = computed(() => {
    if (!restoreCandidate.value || !baselineFields.value) return [];
    const beforeFiles = virtualFileTextFromEditorFields(baselineFields.value);
    const afterFiles = virtualFileTextFromEditorFields(
      workingCopyFieldsFromRecord(restoreCandidate.value),
    );

    return VIRTUAL_FILE_IDS.map((virtualFileId) => ({
      virtualFileId,
      beforeText: beforeFiles[virtualFileId],
      afterText: afterFiles[virtualFileId],
    }));
  });

  const checkpointSummaries = computed<EditorWorkingCopyCheckpointSummary[]>(() =>
    checkpoints.value.map((checkpoint) => ({
      id: checkpoint.checkpoint_id,
      kind: checkpoint.kind,
      label: checkpoint.label?.trim() || "Återställningspunkt",
      createdAt: checkpoint.created_at,
    })),
  );

  const pinnedCheckpointCount = computed(
    () => checkpoints.value.filter((checkpoint) => checkpoint.kind === "pinned").length,
  );

  function applyFields(nextFields: EditorWorkingCopyFields): void {
    fields.entrypoint.value = nextFields.entrypoint;
    fields.sourceCode.value = nextFields.sourceCode;
    fields.settingsSchemaText.value = nextFields.settingsSchemaText;
    fields.inputSchemaText.value = nextFields.inputSchemaText;
    fields.usageInstructions.value = nextFields.usageInstructions;
  }

  async function stashRestoreCandidate(candidate: WorkingCopyHeadRecord): Promise<boolean> {
    if (!canPersist.value || !userId.value || !toolId.value) return false;

    const candidateFields = workingCopyFieldsFromRecord(candidate);
    const fingerprint = fieldsFingerprint(candidateFields);

    try {
      await createCheckpoint({
        userId: userId.value,
        toolId: toolId.value,
        baseVersionId: candidate.base_version_id ?? baseVersionId.value,
        fields: candidateFields,
        kind: "auto",
        label: "Tidigare lokalt arbetsexemplar",
        expiresAt: Date.now() + AUTO_CHECKPOINT_TTL_DAYS * 24 * 60 * 60 * 1000,
      });
      lastAutoCheckpointFingerprint = fingerprint;
      await trimAutoCheckpoints({
        userId: userId.value,
        toolId: toolId.value,
        cap: AUTO_CHECKPOINT_CAP,
      });
      await refreshCheckpoints();
      notify.success("Tidigare lokalt arbetsexemplar sparat i lokal historik.");
      return true;
    } catch {
      if (!hasWarnedCheckpointFailure) {
        hasWarnedCheckpointFailure = true;
        notify.warning("Kunde inte spara tidigare lokalt arbetsexemplar i lokal historik.");
      }
      return false;
    }
  }

  async function persistHeadNow(params: {
    force?: boolean;
    fields?: EditorWorkingCopyFields;
    baseVersionId?: string | null;
  } = {}): Promise<void> {
    if (!canPersist.value || !userId.value || !toolId.value) return;
    if (!hasDirtyChanges.value && !params.force) return;
    if (!baselineFields.value && !params.force) return;

    try {
      const record = await saveWorkingCopyHead({
        userId: userId.value,
        toolId: toolId.value,
        baseVersionId: params.baseVersionId ?? baseVersionId.value,
        fields: params.fields ?? currentFields.value,
      });
      workingCopyHead.value = record;
    } catch {
      if (!hasWarnedHeadSaveFailure) {
        hasWarnedHeadSaveFailure = true;
        notify.warning("Kunde inte spara arbetsexemplar lokalt.");
      }
    }
  }

  function scheduleHeadSave(): void {
    if (!canPersist.value || !hasDirtyChanges.value) return;
    if (!baselineFields.value) return;
    if (isRestorePromptOpen.value && restoreCandidate.value) return;

    if (headSaveTimer) {
      clearTimeout(headSaveTimer);
    }

    headSaveTimer = setTimeout(() => {
      headSaveTimer = null;
      void persistHeadNow();
    }, HEAD_SAVE_DEBOUNCE_MS);
  }

  async function refreshCheckpoints(): Promise<void> {
    if (!canPersist.value || !userId.value || !toolId.value) {
      checkpoints.value = [];
      return;
    }

    try {
      checkpoints.value = await listCheckpoints({
        userId: userId.value,
        toolId: toolId.value,
      });
    } catch {
      checkpoints.value = [];
      notify.warning("Kunde inte ladda lokala återställningspunkter.");
    }
  }

  async function loadWorkingCopy(): Promise<void> {
    if (!canPersist.value || !userId.value || !toolId.value || !baselineFields.value) {
      workingCopyHead.value = null;
      restoreCandidate.value = null;
      isRestorePromptOpen.value = false;
      return;
    }

    isLoading.value = true;
    try {
      const record = await getWorkingCopyHead({
        userId: userId.value,
        toolId: toolId.value,
      });
      workingCopyHead.value = record;

      if (!record) {
        restoreCandidate.value = null;
        isRestorePromptOpen.value = false;
      } else {
        const headFields = workingCopyFieldsFromRecord(record);
        if (!areFieldsEqual(headFields, baselineFields.value)) {
          restoreCandidate.value = record;
          isRestorePromptOpen.value = true;
        } else {
          restoreCandidate.value = null;
          isRestorePromptOpen.value = false;
        }
      }
    } finally {
      isLoading.value = false;
    }

    await refreshCheckpoints();
  }

  async function createAutoCheckpoint(label: string, options: { force?: boolean } = {}): Promise<void> {
    if (!canPersist.value || !userId.value || !toolId.value) return;
    if (!hasDirtyChanges.value && !options.force) return;
    if (!baselineFields.value && !options.force) return;

    const snapshot = currentFields.value;
    const fingerprint = fieldsFingerprint(snapshot);
    if (!options.force && fingerprint === lastAutoCheckpointFingerprint) {
      return;
    }

    try {
      await createCheckpoint({
        userId: userId.value,
        toolId: toolId.value,
        baseVersionId: baseVersionId.value,
        fields: snapshot,
        kind: "auto",
        label,
        expiresAt: Date.now() + AUTO_CHECKPOINT_TTL_DAYS * 24 * 60 * 60 * 1000,
      });
      lastAutoCheckpointFingerprint = fingerprint;
      await trimAutoCheckpoints({
        userId: userId.value,
        toolId: toolId.value,
        cap: AUTO_CHECKPOINT_CAP,
      });
      await refreshCheckpoints();
    } catch {
      if (!hasWarnedCheckpointFailure) {
        hasWarnedCheckpointFailure = true;
        notify.warning("Kunde inte skapa automatisk återställningspunkt.");
      }
    }
  }

  async function createPinnedCheckpoint(label: string): Promise<void> {
    if (!canPersist.value || !userId.value || !toolId.value) return;
    if (pinnedCheckpointCount.value >= PINNED_CHECKPOINT_CAP) {
      notify.warning(`Du har redan ${PINNED_CHECKPOINT_CAP} sparade punkter.`);
      return;
    }

    if (baselineFields.value && !hasDirtyChanges.value) {
      notify.info("Inga osparade ändringar att spara.");
      return;
    }

    isCheckpointBusy.value = true;
    try {
      await createCheckpoint({
        userId: userId.value,
        toolId: toolId.value,
        baseVersionId: baseVersionId.value,
        fields: currentFields.value,
        kind: "pinned",
        label: label.trim() || "Manuell återställningspunkt",
        expiresAt: null,
      });
      await refreshCheckpoints();
      notify.success("Återställningspunkt sparad.");
    } catch {
      notify.warning("Kunde inte skapa återställningspunkt.");
    } finally {
      isCheckpointBusy.value = false;
    }
  }

  async function restoreCheckpoint(checkpointId: string): Promise<void> {
    const checkpoint =
      checkpoints.value.find((item) => item.checkpoint_id === checkpointId) ?? null;
    if (!checkpoint) {
      notify.warning("Återställningspunkten hittades inte.");
      return;
    }

    const restoredFields = checkpointFieldsFromRecord(checkpoint);
    applyFields(restoredFields);
    await persistHeadNow({
      force: true,
      fields: restoredFields,
      baseVersionId: checkpoint.base_version_id ?? baseVersionId.value,
    });
  }

  async function removeCheckpoint(checkpointId: string): Promise<void> {
    if (!canPersist.value || !userId.value || !toolId.value) return;
    try {
      await deleteCheckpoint({
        userId: userId.value,
        toolId: toolId.value,
        checkpointId,
      });
      await refreshCheckpoints();
      notify.success("Återställningspunkten togs bort.");
    } catch {
      notify.warning("Kunde inte ta bort återställningspunkten.");
    }
  }

  async function restoreWorkingCopy(): Promise<void> {
    const candidate = restoreCandidate.value;
    if (!candidate) return;
    const restoredFields = workingCopyFieldsFromRecord(candidate);
    applyFields(restoredFields);
    isRestorePromptOpen.value = false;
    restoreCandidate.value = null;
    await persistHeadNow({
      force: true,
      fields: restoredFields,
      baseVersionId: candidate.base_version_id ?? baseVersionId.value,
    });
  }

  async function discardWorkingCopy(): Promise<void> {
    if (!canPersist.value || !userId.value || !toolId.value) return;
    try {
      await clearWorkingCopyData({ userId: userId.value, toolId: toolId.value });
      workingCopyHead.value = null;
      restoreCandidate.value = null;
      isRestorePromptOpen.value = false;
      checkpoints.value = [];
    } catch {
      notify.warning("Kunde inte rensa lokalt arbetsexemplar.");
    }
  }

  async function restoreServerVersion(): Promise<void> {
    if (!baselineFields.value) return;
    applyFields(baselineFields.value);
    await discardWorkingCopy();
  }

  function startAutoCheckpointInterval(): void {
    if (autoCheckpointTimer) return;
    autoCheckpointTimer = setInterval(() => {
      void createAutoCheckpoint("Autosparad");
    }, AUTO_CHECKPOINT_INTERVAL_MS);
  }

  function stopAutoCheckpointInterval(): void {
    if (autoCheckpointTimer) {
      clearInterval(autoCheckpointTimer);
      autoCheckpointTimer = null;
    }
  }

  function handlePageHide(): void {
    if (!hasDirtyChanges.value) return;
    void persistHeadNow({ force: true });
    void createAutoCheckpoint("Autosparad", { force: true });
  }

  function handleVisibilityChange(): void {
    if (document.visibilityState !== "hidden") return;
    if (!hasDirtyChanges.value) return;
    void persistHeadNow({ force: true });
    void createAutoCheckpoint("Autosparad", { force: true });
  }

  if (typeof window !== "undefined" && typeof document !== "undefined") {
    window.addEventListener("pagehide", handlePageHide);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    onScopeDispose(() => {
      window.removeEventListener("pagehide", handlePageHide);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    });
  }

  watch(
    () => [
      userId.value,
      toolId.value,
      initialSnapshot.value,
    ] as const,
    () => {
      void loadWorkingCopy();
    },
    { immediate: true },
  );

  watch(
    () => [
      fields.entrypoint.value,
      fields.sourceCode.value,
      fields.settingsSchemaText.value,
      fields.inputSchemaText.value,
      fields.usageInstructions.value,
    ],
    () => {
      scheduleHeadSave();
    },
  );

  watch(
    () => hasDirtyChanges.value,
    async (dirty) => {
      if (dirty && canPersist.value) {
        startAutoCheckpointInterval();
      } else {
        stopAutoCheckpointInterval();
      }

      if (dirty && isRestorePromptOpen.value && restoreCandidate.value) {
        if (headSaveTimer) {
          clearTimeout(headSaveTimer);
          headSaveTimer = null;
        }

        const candidate = restoreCandidate.value;
        const stashed = await stashRestoreCandidate(candidate);
        if (stashed) {
          isRestorePromptOpen.value = false;
          restoreCandidate.value = null;
          scheduleHeadSave();
        }
      } else if (dirty && isRestorePromptOpen.value) {
        isRestorePromptOpen.value = false;
      }
      if (!dirty && headSaveTimer) {
        clearTimeout(headSaveTimer);
        headSaveTimer = null;
      }
    },
    { immediate: true },
  );

  onScopeDispose(() => {
    if (headSaveTimer) {
      clearTimeout(headSaveTimer);
      headSaveTimer = null;
    }
    stopAutoCheckpointInterval();
  });

  return {
    isLoading,
    isRestorePromptOpen,
    hasRestoreCandidate,
    restoreDiffItems,
    workingCopyUpdatedAt: computed(() => restoreCandidate.value?.updated_at ?? null),
    restoreWorkingCopy,
    discardWorkingCopy,
    restoreServerVersion,
    checkpointSummaries,
    pinnedCheckpointCount,
    pinnedCheckpointLimit: PINNED_CHECKPOINT_CAP,
    isCheckpointBusy,
    createPinnedCheckpoint,
    restoreCheckpoint,
    removeCheckpoint,
    refreshCheckpoints,
    createAutoCheckpoint,
    createBeforeSaveCheckpoint: () => createAutoCheckpoint("Före sparning", { force: true }),
    createBeforeAiApplyCheckpoint: () => createAutoCheckpoint("Före AI-ändring", { force: true }),
    workingCopyProvider: async () => {
      if (workingCopyHead.value) {
        return workingCopyFieldsFromRecord(workingCopyHead.value);
      }
      if (!canPersist.value || !userId.value || !toolId.value) return null;
      const record = await getWorkingCopyHead({ userId: userId.value, toolId: toolId.value });
      return record ? workingCopyFieldsFromRecord(record) : null;
    },
  };
}
