/**
 * Undo and redo state of the last applied edit-ops proposal.
 *
 * Remembers the files before and after the last apply and which side the
 * editor currently shows. Undo and redo restore a side only while the editor
 * still holds exactly the other side; any later edit makes the teacher return
 * through the restore points instead.
 */

import { computed, ref, watch, type Ref } from "vue";

import {
  applyVirtualFiles,
  createAppliedSnapshot,
  type AppliedEditOpsSnapshot,
  type EditorFieldRefs,
} from "./editOpsSnapshots";
import type { VirtualFileTextMap } from "../virtualFiles";

type UseEditOpsHistoryOptions = {
  isReadOnly: Readonly<Ref<boolean>>;
  isApplying: Readonly<Ref<boolean>>;
  fields: EditorFieldRefs;
  currentFingerprint: Readonly<Ref<string>>;
};

export function useEditOpsHistory(options: UseEditOpsHistoryOptions) {
  const { isReadOnly, isApplying, fields, currentFingerprint } = options;

  const lastApplied = ref<AppliedEditOpsSnapshot | null>(null);
  const aiPosition = ref<"after" | "before">("after");
  const undoError = ref<string | null>(null);

  const undoDisabledReason = computed(() => {
    if (!lastApplied.value) return null;
    if (isReadOnly.value) return "Kodredigeraren är låst för redigering.";
    if (aiPosition.value !== "after") {
      return "AI-ändringen är redan återställd.";
    }
    if (currentFingerprint.value !== lastApplied.value.afterFingerprint) {
      return "Ändringar har gjorts efter AI-ändringen. Återställ via återställningspunkter.";
    }
    return null;
  });

  const canUndo = computed(
    () =>
      Boolean(lastApplied.value) &&
      !isReadOnly.value &&
      !undoDisabledReason.value &&
      !isApplying.value,
  );

  const redoDisabledReason = computed(() => {
    if (!lastApplied.value) return null;
    if (isReadOnly.value) return "Kodredigeraren är låst för redigering.";
    if (aiPosition.value !== "before") {
      return "Ingen AI-ändring att återställa.";
    }
    if (currentFingerprint.value !== lastApplied.value.beforeFingerprint) {
      return "Ändringar har gjorts efter återställning. Återställ via återställningspunkter.";
    }
    return null;
  });

  const canRedo = computed(
    () =>
      Boolean(lastApplied.value) &&
      !isReadOnly.value &&
      !redoDisabledReason.value &&
      !isApplying.value,
  );

  /** Remember an apply so the teacher can undo it. */
  function recordApplied(beforeFiles: VirtualFileTextMap, afterFiles: VirtualFileTextMap): void {
    lastApplied.value = createAppliedSnapshot(beforeFiles, afterFiles);
    aiPosition.value = "after";
  }

  function undoLastApply(): boolean {
    undoError.value = null;
    if (!lastApplied.value) return false;
    if (!canUndo.value) {
      undoError.value = undoDisabledReason.value ?? "Det gick inte att ångra.";
      return false;
    }

    applyVirtualFiles(fields, lastApplied.value.beforeFiles);
    aiPosition.value = "before";
    return true;
  }

  function redoLastApply(): boolean {
    undoError.value = null;
    if (!lastApplied.value) return false;
    if (!canRedo.value) {
      undoError.value = redoDisabledReason.value ?? "Det gick inte att återställa.";
      return false;
    }

    applyVirtualFiles(fields, lastApplied.value.afterFiles);
    aiPosition.value = "after";
    return true;
  }

  watch(
    () => currentFingerprint.value,
    () => {
      if (!lastApplied.value) return;
      if (currentFingerprint.value !== lastApplied.value.afterFingerprint && undoError.value) {
        undoError.value = null;
      }
    },
  );

  return {
    lastApplied,
    aiPosition,
    undoError,
    canUndo,
    undoDisabledReason,
    canRedo,
    redoDisabledReason,
    recordApplied,
    undoLastApply,
    redoLastApply,
  };
}
