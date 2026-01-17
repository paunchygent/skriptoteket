import { computed, type Ref } from "vue";
import type { RouteLocationNormalizedLoaded, Router } from "vue-router";

import type { components } from "../../api/openapi";
import { useHelp } from "../../components/help/useHelp";
import type { UiNotifier } from "../notify";
import { useEditorWorkflowActions } from "./useEditorWorkflowActions";

type EditorBootResponse = components["schemas"]["EditorBootResponse"];
type SelectedVersion = EditorBootResponse["selected_version"];

type UseScriptEditorWorkflowStateOptions = {
  selectedVersion: Readonly<Ref<SelectedVersion | null>>;
  metadataSlug: Readonly<Ref<string>>;
  selectedProfessionIds: Readonly<Ref<string[]>>;
  selectedCategoryIds: Readonly<Ref<string[]>>;
  route: RouteLocationNormalizedLoaded;
  router: Router;
  reloadEditor: () => Promise<void>;
  notify: UiNotifier;
};

export function useScriptEditorWorkflowState(options: UseScriptEditorWorkflowStateOptions) {
  const {
    selectedVersion,
    metadataSlug,
    selectedProfessionIds,
    selectedCategoryIds,
    route,
    router,
    reloadEditor,
    notify,
  } = options;
  const help = useHelp();

  const {
    isModalOpen: isWorkflowModalOpen,
    activeAction: activeWorkflowAction,
    actionMeta: workflowActionMeta,
    showNoteField: showWorkflowNoteField,
    note: workflowNote,
    workflowError,
    isSubmitting: isWorkflowSubmitting,
    canSubmitReview,
    submitReviewBlockers,
    submitReviewTooltip,
    canPublish,
    canRequestChanges,
    canRollback,
    openRollbackForVersion,
    openAction: openWorkflowAction,
    closeAction: closeWorkflowModal,
    submitAction: submitWorkflowAction,
  } = useEditorWorkflowActions({
    selectedVersion,
    toolSlug: metadataSlug,
    selectedProfessionIds,
    selectedCategoryIds,
    route,
    router,
    reloadEditor,
    notify,
  });

  const confirmButtonClass = computed(() => {
    switch (activeWorkflowAction.value) {
      case "publish":
        return "btn-cta";
      case "submit_review":
        return "btn-primary";
      case "request_changes":
        return "btn-ghost";
      case "rollback":
        return "btn-cta";
      default:
        return "btn-primary";
    }
  });

  const submitReviewBlockedItems = computed(() => {
    if (activeWorkflowAction.value !== "submit_review") {
      return [];
    }
    return submitReviewBlockers.value.map((blocker) => blocker.message);
  });

  function openEditorHelp(): void {
    help.showTopic("admin_editor");
    help.open();
    closeWorkflowModal();
  }

  return {
    isWorkflowModalOpen,
    activeWorkflowAction,
    workflowActionMeta,
    showWorkflowNoteField,
    workflowNote,
    workflowError,
    isWorkflowSubmitting,
    canSubmitReview,
    submitReviewBlockers,
    submitReviewTooltip,
    canPublish,
    canRequestChanges,
    canRollback,
    openRollbackForVersion,
    openWorkflowAction,
    closeWorkflowModal,
    submitWorkflowAction,
    confirmButtonClass,
    submitReviewBlockedItems,
    openEditorHelp,
  };
}
