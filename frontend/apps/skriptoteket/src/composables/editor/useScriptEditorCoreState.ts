import type { EditorView } from "@codemirror/view";
import { computed, onErrorCaptured, ref, shallowRef } from "vue";
import { storeToRefs } from "pinia";
import { useRoute, useRouter } from "vue-router";

import { useEditorSchemaParsing } from "./useEditorSchemaParsing";
import { useEditorSchemaValidation } from "./useEditorSchemaValidation";
import { useDraftLock } from "./useDraftLock";
import { useScriptEditor } from "./useScriptEditor";
import type { UiNotifier } from "../notify";
import { useToast } from "../useToast";
import { useAuthStore } from "../../stores/auth";
import { useLayoutStore } from "../../stores/layout";

export function useScriptEditorCoreState() {
  const route = useRoute();
  const router = useRouter();
  const auth = useAuthStore();
  const layout = useLayoutStore();
  const toast = useToast();
  const { focusMode } = storeToRefs(layout);

  const renderError = ref<string | null>(null);

  const notify: UiNotifier = {
    info: (message: string) => toast.info(message),
    success: (message: string) => toast.success(message),
    warning: (message: string) => toast.warning(message),
    failure: (message: string) => toast.failure(message),
  };

  const editorView = shallowRef<EditorView | null>(null);

  const toolId = computed(() => {
    const param = route.params.toolId;
    return typeof param === "string" ? param : "";
  });
  const versionId = computed(() => {
    const param = route.params.versionId;
    return typeof param === "string" ? param : "";
  });

  const canEditTaxonomy = computed(() => auth.hasAtLeastRole("admin"));
  const canEditMaintainers = computed(() => auth.hasAtLeastRole("admin"));
  const canRollbackVersions = computed(() => auth.hasAtLeastRole("superuser"));
  const canForceTakeover = computed(() => auth.hasAtLeastRole("admin"));
  const currentUserId = computed(() => auth.user?.id ?? null);

  const {
    editor,
    entrypoint,
    sourceCode,
    settingsSchemaText,
    inputSchemaText,
    usageInstructions,
    initialSnapshot,
    changeSummary,
    metadataTitle,
    metadataSummary,
    metadataSlug,
    isLoading,
    isSaving,
    isMetadataSaving,
    isSlugSaving,
    errorMessage,
    slugError,
    selectedVersion,
    editorToolId,
    saveButtonLabel,
    saveButtonTitle,
    hasDirtyChanges,
    save,
    saveToolMetadata,
    saveToolSlug,
    applySlugSuggestionFromTitle,
    loadEditor,
  } = useScriptEditor({
    toolId,
    versionId,
    route,
    router,
    notify,
  });

  const { inputSchema, inputSchemaError, settingsSchema, settingsSchemaError } =
    useEditorSchemaParsing({
      inputSchemaText,
      settingsSchemaText,
    });

  const draftHeadId = computed(() => editor.value?.draft_head_id ?? null);
  const initialDraftLock = computed(() => editor.value?.draft_lock ?? null);
  const {
    state: draftLockState,
    isReadOnly,
    isLocking,
    expiresAt,
    statusMessage: draftLockStatus,
    lockError: draftLockError,
    forceTakeover,
  } = useDraftLock({
    toolId: editorToolId,
    draftHeadId,
    initialLock: initialDraftLock,
  });

  const {
    issuesBySchema: schemaIssuesBySchema,
    hasBlockingIssues: hasBlockingSchemaIssues,
    isValidating: isSchemaValidating,
    validationError: schemaValidationError,
    validateNow: validateSchemasNow,
  } = useEditorSchemaValidation({
    toolId: editorToolId,
    inputSchema,
    settingsSchema,
    inputSchemaError,
    settingsSchemaError,
    isReadOnly,
  });

  const canEditSlug = computed(
    () => auth.hasAtLeastRole("admin") && editor.value?.tool.is_published === false
  );

  const entrypointOptions = ["run_tool"];

  const lockBadge = computed(() => {
    if (draftLockState.value === "owner") {
      return {
        label: "Redigeringslås aktivt",
        tone: "success" as const,
      };
    }
    if (draftLockState.value === "acquiring") {
      return {
        label: "Säkrar redigeringslås...",
        tone: "neutral" as const,
      };
    }
    return null;
  });

  onErrorCaptured((error) => {
    renderError.value = error instanceof Error ? error.message : String(error);
    return false;
  });

  return {
    route,
    router,
    auth,
    layout,
    focusMode,
    notify,
    renderError,
    editorView,
    toolId,
    versionId,
    canEditTaxonomy,
    canEditMaintainers,
    canRollbackVersions,
    canForceTakeover,
    currentUserId,
    editor,
    entrypoint,
    sourceCode,
    settingsSchemaText,
    inputSchemaText,
    usageInstructions,
    initialSnapshot,
    changeSummary,
    metadataTitle,
    metadataSummary,
    metadataSlug,
    isLoading,
    isSaving,
    isMetadataSaving,
    isSlugSaving,
    errorMessage,
    slugError,
    selectedVersion,
    editorToolId,
    saveButtonLabel,
    saveButtonTitle,
    hasDirtyChanges,
    save,
    saveToolMetadata,
    saveToolSlug,
    applySlugSuggestionFromTitle,
    loadEditor,
    inputSchema,
    inputSchemaError,
    settingsSchema,
    settingsSchemaError,
    schemaIssuesBySchema,
    hasBlockingSchemaIssues,
    isSchemaValidating,
    schemaValidationError,
    validateSchemasNow,
    canEditSlug,
    entrypointOptions,
    draftLockState,
    isReadOnly,
    isLocking,
    expiresAt,
    draftLockStatus,
    draftLockError,
    forceTakeover,
    lockBadge,
  };
}
