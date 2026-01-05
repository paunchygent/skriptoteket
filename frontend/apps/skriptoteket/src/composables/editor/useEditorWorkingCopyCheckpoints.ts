import { computed, ref, type Ref } from "vue";

import type { UiNotifier } from "../notify";
import {
  AUTO_CHECKPOINT_CAP,
  AUTO_CHECKPOINT_TTL_DAYS,
  PINNED_CHECKPOINT_CAP,
  checkpointFieldsFromRecord,
  createCheckpoint,
  deleteCheckpoint,
  listCheckpoints,
  trimAutoCheckpoints,
  workingCopyFieldsFromRecord,
  type CheckpointRecord,
  type EditorWorkingCopyFields,
  type WorkingCopyHeadRecord,
} from "./editorPersistence";
import { fieldsFingerprint } from "./editorWorkingCopyFingerprint";

type PersistHeadNow = (params?: {
  force?: boolean;
  fields?: EditorWorkingCopyFields;
  baseVersionId?: string | null;
}) => Promise<void>;

type ApplyFields = (fields: EditorWorkingCopyFields) => void;

export function useEditorWorkingCopyCheckpoints(options: {
  canPersist: Readonly<Ref<boolean>>;
  userId: Readonly<Ref<string | null>>;
  toolId: Readonly<Ref<string>>;
  baseVersionId: Readonly<Ref<string | null>>;
  hasDirtyChanges: Readonly<Ref<boolean>>;
  baselineFields: Readonly<Ref<EditorWorkingCopyFields | null>>;
  currentFields: Readonly<Ref<EditorWorkingCopyFields>>;
  notify: UiNotifier;
  applyFields: ApplyFields;
  persistHeadNow: PersistHeadNow;
}) {
  const {
    canPersist,
    userId,
    toolId,
    baseVersionId,
    hasDirtyChanges,
    baselineFields,
    currentFields,
    notify,
    applyFields,
    persistHeadNow,
  } = options;

  const checkpoints = ref<CheckpointRecord[]>([]);
  const isCheckpointBusy = ref(false);
  const pinnedCheckpointCount = computed(
    () => checkpoints.value.filter((checkpoint) => checkpoint.kind === "pinned").length,
  );

  let lastAutoCheckpointFingerprint = "";
  let hasWarnedCheckpointFailure = false;

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

  return {
    checkpoints,
    pinnedCheckpointCount,
    isCheckpointBusy,
    refreshCheckpoints,
    createAutoCheckpoint,
    createPinnedCheckpoint,
    restoreCheckpoint,
    removeCheckpoint,
    stashRestoreCandidate,
  };
}
