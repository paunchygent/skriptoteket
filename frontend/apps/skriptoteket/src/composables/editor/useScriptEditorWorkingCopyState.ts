import { computed, type Ref } from "vue";

import type { components } from "../../api/openapi";
import type { UiNotifier } from "../notify";
import { useEditorWorkingCopy, type EditorBaselineSnapshot } from "./useEditorWorkingCopy";

type EditorBootResponse = components["schemas"]["EditorBootResponse"];
type SelectedVersion = EditorBootResponse["selected_version"];

type UseScriptEditorWorkingCopyStateOptions = {
  userId: Readonly<Ref<string | null>>;
  toolId: Readonly<Ref<string>>;
  selectedVersion: Readonly<Ref<SelectedVersion | null>>;
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
  confirmDiscardChanges: (message: string) => boolean;
};

export function useScriptEditorWorkingCopyState(options: UseScriptEditorWorkingCopyStateOptions) {
  const {
    userId,
    toolId,
    selectedVersion,
    hasDirtyChanges,
    initialSnapshot,
    fields,
    notify,
    confirmDiscardChanges,
  } = options;

  const workingCopy = useEditorWorkingCopy({
    userId,
    toolId,
    baseVersionId: computed(() => selectedVersion.value?.id ?? null),
    hasDirtyChanges,
    initialSnapshot,
    fields,
    notify,
  });

  const {
    isRestorePromptOpen,
    hasWorkingCopyHead,
    restoreDiffItems,
    workingCopyUpdatedAt,
    checkpointSummaries,
    pinnedCheckpointCount,
    pinnedCheckpointLimit,
    isCheckpointBusy,
    restoreWorkingCopy,
    discardWorkingCopy,
    restoreServerVersion,
    createBeforeSaveCheckpoint,
    createBeforeAiApplyCheckpoint,
    createPinnedCheckpoint,
    restoreCheckpoint,
    removeCheckpoint,
    workingCopyProvider,
  } = workingCopy;

  const aiFields = {
    entrypoint: fields.entrypoint,
    sourceCode: fields.sourceCode,
    settingsSchemaText: fields.settingsSchemaText,
    inputSchemaText: fields.inputSchemaText,
    usageInstructions: fields.usageInstructions,
  };

  function handleRestoreServerVersion(): void {
    if (pinnedCheckpointCount.value > 0) {
      const message = hasDirtyChanges.value
        ? "Återställ till serverversion och rensa lokalt? Dina osparade ändringar försvinner och "
          + `${pinnedCheckpointCount.value} manuella återställningspunkter tas bort.`
        : "Rensa lokalt arbetsexemplar? "
          + `${pinnedCheckpointCount.value} manuella återställningspunkter tas bort.`;

      if (!window.confirm(message)) {
        return;
      }
      void restoreServerVersion();
      return;
    }

    if (!confirmDiscardChanges("Återställ till serverversion och rensa lokalt?")) return;
    void restoreServerVersion();
  }

  function handleDiscardWorkingCopy(): void {
    if (pinnedCheckpointCount.value > 0) {
      const message =
        "Kasta lokalt arbetsexemplar? Det här tar bort lokalt arbetsexemplar och "
        + `${pinnedCheckpointCount.value} manuella återställningspunkter. `
        + "Serverversionen påverkas inte.";
      if (!window.confirm(message)) {
        return;
      }
    }
    void discardWorkingCopy();
  }

  return {
    isRestorePromptOpen,
    hasWorkingCopyHead,
    restoreDiffItems,
    workingCopyUpdatedAt,
    checkpointSummaries,
    pinnedCheckpointCount,
    pinnedCheckpointLimit,
    isCheckpointBusy,
    restoreWorkingCopy,
    discardWorkingCopy,
    restoreServerVersion,
    createBeforeSaveCheckpoint,
    createBeforeAiApplyCheckpoint,
    createPinnedCheckpoint,
    restoreCheckpoint,
    removeCheckpoint,
    workingCopyProvider,
    aiFields,
    handleRestoreServerVersion,
    handleDiscardWorkingCopy,
  };
}
