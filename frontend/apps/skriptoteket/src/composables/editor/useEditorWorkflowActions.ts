import { computed, ref, watch, type Ref } from "vue";
import type { RouteLocationNormalizedLoaded, Router } from "vue-router";

import { apiPost, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { useAuthStore } from "../../stores/auth";
import type { UiNotifier } from "../notify";

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
    title: "Begär publicering",
    description: "Är du säker? Detta skickar utkastet till granskning.",
    confirmLabel: "Begär publicering",
    noteLabel: "Notis till granskare (valfri)",
    notePlaceholder: "Skriv en kort notis…",
    showNote: true,
  },
  publish: {
    title: "Publicera version",
    description: "Publiceringen skapar en ny aktiv version.",
    confirmLabel: "Publicera",
    noteLabel: "Ändra verktygets beskrivning (valfri, lämna tom för att behålla verktygsförfattarens beskrivning)",
    notePlaceholder: "T.ex. uppdaterade regler…",
    showNote: true,
  },
  request_changes: {
    title: "Avslå version",
    description: "Avslå versionen och meddela författaren.",
    confirmLabel: "Avslå",
    noteLabel: "Meddelande till författaren (valfritt)",
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
  notify: UiNotifier;
};

type ActionItem = {
  id: WorkflowAction;
  label: string;
  tone?: "primary" | "danger";
};

export function useEditorWorkflowActions({
  selectedVersion,
  route,
  router,
  reloadEditor,
  notify,
}: UseEditorWorkflowActionsOptions) {
  const auth = useAuthStore();
  const isModalOpen = ref(false);
  const activeAction = ref<WorkflowAction | null>(null);
  const targetVersionId = ref<string | null>(null);
  const note = ref("");
  const workflowError = ref<string | null>(null);
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

  const actionItems = computed<ActionItem[]>(() => {
    const items: ActionItem[] = [];

    if (canSubmitReview.value) {
      items.push({ id: "submit_review", label: ACTION_META.submit_review.title });
    }
    if (canPublish.value) {
      items.push({ id: "publish", label: ACTION_META.publish.title, tone: "primary" });
    }
    if (canRequestChanges.value) {
      items.push({ id: "request_changes", label: ACTION_META.request_changes.title });
    }
    if (canRollback.value) {
      items.push({ id: "rollback", label: ACTION_META.rollback.title, tone: "danger" });
    }

    return items;
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
    targetVersionId.value = null;
    note.value = "";
    workflowError.value = null;
    isModalOpen.value = true;
  }

  function openRollbackForVersion(versionId: string): void {
    if (!auth.hasAtLeastRole("superuser")) {
      return;
    }
    activeAction.value = "rollback";
    targetVersionId.value = versionId;
    note.value = "";
    workflowError.value = null;
    isModalOpen.value = true;
  }

  function closeAction(): void {
    isModalOpen.value = false;
    activeAction.value = null;
    note.value = "";
    targetVersionId.value = null;
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
    const versionId = targetVersionId.value ?? selectedVersion.value?.id ?? null;
    if (!action || !versionId || isSubmitting.value) {
      return;
    }

    isSubmitting.value = true;
    workflowError.value = null;

    const trimmedNote = note.value.trim();
    const noteValue = trimmedNote ? trimmedNote : null;

    try {
      let endpoint = "";
      let body: Record<string, unknown> | undefined;
      let successMessage = "";

      switch (action) {
        case "submit_review":
          endpoint = `/api/v1/editor/tool-versions/${versionId}/submit-review`;
          body = { review_note: noteValue };
          successMessage = "Begär publicering skickad.";
          break;
        case "publish":
          endpoint = `/api/v1/editor/tool-versions/${versionId}/publish`;
          body = { change_summary: noteValue };
          successMessage = "Version publicerad.";
          break;
        case "request_changes":
          endpoint = `/api/v1/editor/tool-versions/${versionId}/request-changes`;
          body = { message: noteValue };
          successMessage = "Versionen avslogs.";
          break;
        case "rollback":
          endpoint = `/api/v1/editor/tool-versions/${versionId}/rollback`;
          successMessage = "Version återställd.";
          break;
        default:
          return;
      }

      const response = await apiPost<WorkflowActionResponse>(endpoint, body);
      notify.success(successMessage);
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
    isSubmitting,
    canSubmitReview,
    canPublish,
    canRequestChanges,
    canRollback,
    actionItems,
    openAction,
    openRollbackForVersion,
    closeAction,
    submitAction,
  };
}
