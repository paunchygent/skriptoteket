import { computed, ref, watch, type Ref } from "vue";
import type { RouteLocationNormalizedLoaded, Router } from "vue-router";

import { apiPost, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { useAuthStore } from "../../stores/auth";

type EditorVersionSummary = components["schemas"]["EditorVersionSummary"];
type WorkflowActionResponse = components["schemas"]["WorkflowActionResponse"];

type WorkflowAction = "submit_review" | "publish" | "request_changes" | "rollback";

type WorkflowActionMeta = {
  title: string;
  description?: string;
  confirmLabel: string;
  noteLabel: string;
  notePlaceholder: string;
  showNote: boolean;
};

const ACTION_META: Record<WorkflowAction, WorkflowActionMeta> = {
  submit_review: {
    title: "Skicka för granskning",
    description: "Skicka utkastet till administratörer för granskning.",
    confirmLabel: "Skicka för granskning",
    noteLabel: "Notis till granskare (valfri)",
    notePlaceholder: "Skriv en kort notis…",
    showNote: true,
  },
  publish: {
    title: "Publicera version",
    description: "Publiceringen skapar en ny aktiv version.",
    confirmLabel: "Publicera",
    noteLabel: "Ändringssammanfattning (valfri)",
    notePlaceholder: "T.ex. uppdaterade regler…",
    showNote: true,
  },
  request_changes: {
    title: "Begär ändringar",
    description: "Begär ändringar och skapa ett nytt utkast.",
    confirmLabel: "Begär ändringar",
    noteLabel: "Meddelande (valfritt)",
    notePlaceholder: "Beskriv vad som behöver ändras…",
    showNote: true,
  },
  rollback: {
    title: "Återställ version",
    description: "Den här versionen blir ny aktiv version.",
    confirmLabel: "Återställ",
    noteLabel: "",
    notePlaceholder: "",
    showNote: false,
  },
};

type UseEditorWorkflowActionsOptions = {
  selectedVersion: Readonly<Ref<EditorVersionSummary | null>>;
  route: RouteLocationNormalizedLoaded;
  router: Router;
  reloadEditor: () => Promise<void>;
};

export function useEditorWorkflowActions({
  selectedVersion,
  route,
  router,
  reloadEditor,
}: UseEditorWorkflowActionsOptions) {
  const auth = useAuthStore();
  const isModalOpen = ref(false);
  const activeAction = ref<WorkflowAction | null>(null);
  const note = ref("");
  const workflowError = ref<string | null>(null);
  const workflowSuccess = ref<string | null>(null);
  const isSubmitting = ref(false);

  const canSubmitReview = computed(() => {
    const version = selectedVersion.value;
    return (
      Boolean(version) &&
      version?.state === "draft" &&
      auth.hasAtLeastRole("contributor")
    );
  });

  const canPublish = computed(() => {
    const version = selectedVersion.value;
    return Boolean(version) && version?.state === "in_review" && auth.hasAtLeastRole("admin");
  });

  const canRequestChanges = computed(() => {
    const version = selectedVersion.value;
    return Boolean(version) && version?.state === "in_review" && auth.hasAtLeastRole("admin");
  });

  const canRollback = computed(() => {
    const version = selectedVersion.value;
    return Boolean(version) && version?.state === "archived" && auth.hasAtLeastRole("superuser");
  });

  const actionMeta = computed<WorkflowActionMeta | null>(() => {
    if (!activeAction.value) {
      return null;
    }
    return ACTION_META[activeAction.value];
  });

  const showNoteField = computed(() => actionMeta.value?.showNote ?? false);

  function openAction(action: WorkflowAction): void {
    activeAction.value = action;
    note.value = "";
    workflowError.value = null;
    isModalOpen.value = true;
  }

  function closeAction(): void {
    isModalOpen.value = false;
    activeAction.value = null;
    note.value = "";
  }

  async function navigateAfterAction(path: string): Promise<void> {
    if (!path || path === route.path) {
      await reloadEditor();
      return;
    }
    await router.push(path);
  }

  async function submitAction(): Promise<void> {
    const action = activeAction.value;
    const version = selectedVersion.value;
    if (!action || !version || isSubmitting.value) {
      return;
    }

    isSubmitting.value = true;
    workflowError.value = null;
    workflowSuccess.value = null;

    const trimmedNote = note.value.trim();
    const noteValue = trimmedNote ? trimmedNote : null;

    try {
      let endpoint = "";
      let body: Record<string, unknown> | undefined;
      let successMessage = "";

      switch (action) {
        case "submit_review":
          endpoint = `/api/v1/editor/tool-versions/${version.id}/submit-review`;
          body = { review_note: noteValue };
          successMessage = "Skickat för granskning.";
          break;
        case "publish":
          endpoint = `/api/v1/editor/tool-versions/${version.id}/publish`;
          body = { change_summary: noteValue };
          successMessage = "Version publicerad.";
          break;
        case "request_changes":
          endpoint = `/api/v1/editor/tool-versions/${version.id}/request-changes`;
          body = { message: noteValue };
          successMessage = "Ändringar begärda.";
          break;
        case "rollback":
          endpoint = `/api/v1/editor/tool-versions/${version.id}/rollback`;
          successMessage = "Version återställd.";
          break;
        default:
          return;
      }

      const response = await apiPost<WorkflowActionResponse>(endpoint, body);
      workflowSuccess.value = successMessage;
      closeAction();
      await navigateAfterAction(response.redirect_url);
    } catch (error: unknown) {
      if (isApiError(error)) {
        workflowError.value = error.message;
      } else if (error instanceof Error) {
        workflowError.value = error.message;
      } else {
        workflowError.value = "Det gick inte att utföra åtgärden.";
      }
    } finally {
      isSubmitting.value = false;
    }
  }

  watch(
    () => route.fullPath,
    () => {
      workflowError.value = null;
      workflowSuccess.value = null;
      closeAction();
    },
  );

  watch(activeAction, () => {
    workflowError.value = null;
  });

  return {
    isModalOpen,
    activeAction,
    actionMeta,
    showNoteField,
    note,
    workflowError,
    workflowSuccess,
    isSubmitting,
    canSubmitReview,
    canPublish,
    canRequestChanges,
    canRollback,
    openAction,
    closeAction,
    submitAction,
  };
}
