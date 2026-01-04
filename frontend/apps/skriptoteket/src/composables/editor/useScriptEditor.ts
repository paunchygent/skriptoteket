import { computed, onMounted, ref, watch, type Ref } from "vue";
import type { RouteLocationNormalizedLoaded, Router } from "vue-router";

import { apiFetch, apiGet, apiPost, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import type { UiNotifier } from "../notify";
import { parseSchemaJsonArrayText } from "./schemaJsonHelpers";

type EditorBootResponse = components["schemas"]["EditorBootResponse"];
type EditorToolMetadataResponse = components["schemas"]["EditorToolMetadataResponse"];
type SaveResult = components["schemas"]["SaveResult"];
type SettingsSchema = NonNullable<EditorBootResponse["settings_schema"]>;
type InputSchema = NonNullable<EditorBootResponse["input_schema"]>;

type UseScriptEditorOptions = {
  toolId: Readonly<Ref<string>>;
  versionId: Readonly<Ref<string>>;
  route: RouteLocationNormalizedLoaded;
  router: Router;
  notify: UiNotifier;
};

type SaveOptions = {
  validateSchemasNow?: () => Promise<boolean>;
  schemaValidationError?: Readonly<Ref<string | null>>;
};

export function useScriptEditor({
  toolId,
  versionId,
  route,
  router,
  notify,
}: UseScriptEditorOptions) {
  const editor = ref<EditorBootResponse | null>(null);
  const entrypoint = ref("");
  const sourceCode = ref("");
  const settingsSchemaText = ref("");
  const inputSchemaText = ref("");
  const usageInstructions = ref("");
  const changeSummary = ref("");
  const metadataTitle = ref("");
  const metadataSummary = ref("");
  const metadataSlug = ref("");
  const slugError = ref<string | null>(null);
  const isSlugSaving = ref(false);

  const isLoading = ref(true);
  const isSaving = ref(false);
  const isMetadataSaving = ref(false);
  const errorMessage = ref<string | null>(null);

  const initialSnapshot = ref<{
    entrypoint: string;
    sourceCode: string;
    settingsSchemaText: string;
    inputSchemaText: string;
    usageInstructions: string;
  } | null>(null);

  const selectedVersion = computed(() => editor.value?.selected_version ?? null);
  const editorToolId = computed(() => editor.value?.tool.id ?? "");

  const saveButtonLabel = computed(() => {
    if (isSaving.value) return "Sparar...";
    return "Spara";
  });

  const hasDirtyChanges = computed(() => {
    if (!initialSnapshot.value) return false;
    return (
      initialSnapshot.value.entrypoint !== entrypoint.value ||
      initialSnapshot.value.sourceCode !== sourceCode.value ||
      initialSnapshot.value.settingsSchemaText !== settingsSchemaText.value ||
      initialSnapshot.value.inputSchemaText !== inputSchemaText.value ||
      initialSnapshot.value.usageInstructions !== usageInstructions.value
    );
  });

  function normalizedOptionalString(value: string): string | null {
    const trimmed = value.trim();
    return trimmed ? trimmed : null;
  }

  function resolveEditorPath(): { path: string | null; soft: boolean } {
    const queryVersion =
      typeof route.query.version === "string" ? route.query.version.trim() : "";
    if (queryVersion) {
      return {
        path: `/api/v1/editor/tool-versions/${encodeURIComponent(queryVersion)}`,
        soft: Boolean(editor.value),
      };
    }

    if (toolId.value !== "") {
      return {
        path: `/api/v1/editor/tools/${encodeURIComponent(toolId.value)}`,
        soft: false,
      };
    }
    if (versionId.value !== "") {
      return {
        path: `/api/v1/editor/tool-versions/${encodeURIComponent(versionId.value)}`,
        soft: false,
      };
    }
    return { path: null, soft: false };
  }

  function applyEditorResponse(response: EditorBootResponse): void {
    editor.value = response;
    entrypoint.value = response.entrypoint;
    sourceCode.value = response.source_code;

    const schema = response.settings_schema;
    settingsSchemaText.value = schema ? JSON.stringify(schema, null, 2) : "";

    const inputSchema = response.input_schema;
    inputSchemaText.value = inputSchema ? JSON.stringify(inputSchema, null, 2) : "";

    usageInstructions.value = response.usage_instructions ?? "";

    changeSummary.value = "";
    metadataTitle.value = response.tool.title;
    metadataSummary.value = response.tool.summary ?? "";
    metadataSlug.value = response.tool.slug;
    initialSnapshot.value = {
      entrypoint: response.entrypoint,
      sourceCode: response.source_code,
      settingsSchemaText: settingsSchemaText.value,
      inputSchemaText: inputSchemaText.value,
      usageInstructions: usageInstructions.value,
    };
  }

  function suggestToolSlugFromTitle(title: string): string {
    const lowered = title.trim().toLowerCase();
    const transliterated = lowered
      .replaceAll("å", "a")
      .replaceAll("ä", "a")
      .replaceAll("ö", "o");

    return transliterated
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-+/, "")
      .replace(/-+$/, "");
  }

  function applySlugSuggestionFromTitle(): void {
    slugError.value = null;

    const suggestion = suggestToolSlugFromTitle(metadataTitle.value);
    if (!suggestion) {
      slugError.value = "Kunde inte skapa ett URL-namn från titeln.";
      return;
    }

    metadataSlug.value = suggestion;
  }

  async function loadEditorFromPath(
    path: string,
    options: { soft?: boolean } = {},
  ): Promise<void> {
    const soft = options.soft ?? false;
    if (!soft) {
      isLoading.value = true;
    }
    errorMessage.value = null;

    try {
      const response = await apiGet<EditorBootResponse>(path);
      applyEditorResponse(response);
    } catch (error: unknown) {
      editor.value = null;
      if (isApiError(error)) {
        errorMessage.value = error.message;
      } else if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = "Det gick inte att ladda editorn.";
      }
    } finally {
      if (!soft) {
        isLoading.value = false;
      }
    }
  }

  async function loadEditor(): Promise<void> {
    const { path, soft } = resolveEditorPath();

    if (!path) {
      errorMessage.value = "Ingen editor hittades.";
      isLoading.value = false;
      editor.value = null;
      return;
    }

    await loadEditorFromPath(path, { soft });
  }

  async function loadEditorForVersion(versionIdValue: string): Promise<void> {
    if (!versionIdValue) {
      return;
    }
    const path = `/api/v1/editor/tool-versions/${encodeURIComponent(versionIdValue)}`;
    await loadEditorFromPath(path, { soft: true });
  }

  async function navigateAfterSave(path: string): Promise<void> {
    if (!path) {
      await loadEditor();
      return;
    }

    if (path === route.path) {
      await loadEditor();
      return;
    }

    await router.push(path);
  }

  async function save(options: SaveOptions = {}): Promise<void> {
    if (!editor.value || isSaving.value) return;

    const entrypointValue = entrypoint.value.trim();
    if (!entrypointValue) {
      errorMessage.value = "Startfunktion krävs.";
      return;
    }

    isSaving.value = true;
    errorMessage.value = null;

    try {
      const summaryValue = normalizedOptionalString(changeSummary.value);

      const settingsSchemaResult = parseSchemaJsonArrayText<SettingsSchema[number]>(
        settingsSchemaText.value,
        "Inställningsschemat",
        null,
      );
      if (settingsSchemaResult.error) {
        errorMessage.value = settingsSchemaResult.error;
        return;
      }
      const settingsSchema = settingsSchemaResult.value as SettingsSchema | null;

      const inputSchemaResult = parseSchemaJsonArrayText<InputSchema[number]>(
        inputSchemaText.value,
        "Indata-schemat",
        [],
      );
      if (inputSchemaResult.error) {
        errorMessage.value = inputSchemaResult.error;
        return;
      }
      const inputSchema = (inputSchemaResult.value ?? []) as InputSchema;

      if (options.validateSchemasNow) {
        const valid = await options.validateSchemasNow();
        if (!valid) {
          errorMessage.value =
            options.schemaValidationError?.value ??
            "Schemat innehåller valideringsfel. Åtgärda felen innan du sparar.";
          return;
        }
      }

      if (editor.value.save_mode === "snapshot") {
        const version = selectedVersion.value;
        if (!version) {
          errorMessage.value = "Versionen stämmer inte längre. Ladda om och försök igen.";
          return;
        }

        const response = await apiPost<SaveResult>(
          `/api/v1/editor/tool-versions/${version.id}/save`,
          {
            entrypoint: entrypointValue,
            source_code: sourceCode.value,
            settings_schema: settingsSchema,
            input_schema: inputSchema,
            usage_instructions: normalizedOptionalString(usageInstructions.value),
            change_summary: summaryValue,
            expected_parent_version_id: version.id,
          },
        );

        notify.success("Sparat.");
        await navigateAfterSave(response.redirect_url);
        return;
      }

      const response = await apiPost<SaveResult>(
        `/api/v1/editor/tools/${editor.value.tool.id}/draft`,
        {
          entrypoint: entrypointValue,
          source_code: sourceCode.value,
          settings_schema: settingsSchema,
          input_schema: inputSchema,
          usage_instructions: normalizedOptionalString(usageInstructions.value),
          change_summary: summaryValue,
          derived_from_version_id: editor.value.derived_from_version_id,
        },
      );

      notify.success("Utkast skapat.");
      await navigateAfterSave(response.redirect_url);
    } catch (error: unknown) {
      if (isApiError(error)) {
        if (error.status === 409) {
          notify.warning(error.message);
        } else {
          notify.failure(error.message);
        }
      } else if (error instanceof Error) {
        notify.failure(error.message);
      } else {
        notify.failure("Det gick inte att spara just nu.");
      }
    } finally {
      isSaving.value = false;
    }
  }

  async function saveToolMetadata(): Promise<void> {
    if (!editor.value || isMetadataSaving.value) return;

    const normalizedTitle = metadataTitle.value.trim();
    if (!normalizedTitle) {
      errorMessage.value = "Titel krävs.";
      return;
    }

    isMetadataSaving.value = true;
    errorMessage.value = null;

    try {
      const response = await apiFetch<EditorToolMetadataResponse>(
        `/api/v1/editor/tools/${encodeURIComponent(editor.value.tool.id)}/metadata`,
        {
          method: "PATCH",
          body: {
            title: normalizedTitle,
            summary: normalizedOptionalString(metadataSummary.value),
          },
        },
      );

      editor.value = {
        ...editor.value,
        tool: {
          ...editor.value.tool,
          slug: response.slug,
          title: response.title,
          summary: response.summary,
        },
      };
      metadataSlug.value = response.slug;
      metadataTitle.value = response.title;
      metadataSummary.value = response.summary ?? "";
      notify.success("Metadata sparad.");
    } catch (error: unknown) {
      if (isApiError(error)) {
        if (error.status === 409) {
          notify.warning(error.message);
        } else {
          notify.failure(error.message);
        }
      } else if (error instanceof Error) {
        notify.failure(error.message);
      } else {
        notify.failure("Det gick inte att spara metadata just nu.");
      }
    } finally {
      isMetadataSaving.value = false;
    }
  }

  async function saveToolSlug(): Promise<void> {
    if (!editor.value || isSlugSaving.value) return;

    const normalizedSlug = metadataSlug.value.trim();
    if (!normalizedSlug) {
      slugError.value = "URL-namn krävs.";
      return;
    }

    isSlugSaving.value = true;
    slugError.value = null;

    try {
      const response = await apiFetch<EditorToolMetadataResponse>(
        `/api/v1/editor/tools/${encodeURIComponent(editor.value.tool.id)}/slug`,
        {
          method: "PATCH",
          body: {
            slug: normalizedSlug,
          },
        },
      );

      editor.value = {
        ...editor.value,
        tool: {
          ...editor.value.tool,
          slug: response.slug,
        },
      };
      metadataSlug.value = response.slug;
      notify.success("URL-namn sparat.");
    } catch (error: unknown) {
      if (isApiError(error)) {
        slugError.value = error.message;
      } else if (error instanceof Error) {
        slugError.value = error.message;
      } else {
        slugError.value = "Det gick inte att spara URL-namn.";
      }
    } finally {
      isSlugSaving.value = false;
    }
  }

  onMounted(() => {
    void loadEditor();
  });

  watch(
    () => route.fullPath,
    () => {
      void loadEditor();
    },
  );

  return {
    editor,
    entrypoint,
    sourceCode,
    settingsSchemaText,
    inputSchemaText,
    usageInstructions,
    changeSummary,
    isLoading,
    isSaving,
    isMetadataSaving,
    errorMessage,
    selectedVersion,
    editorToolId,
    saveButtonLabel,
    hasDirtyChanges,
    loadEditor,
    loadEditorForVersion,
    save,
    metadataTitle,
    metadataSummary,
    metadataSlug,
    saveToolMetadata,
    saveToolSlug,
    applySlugSuggestionFromTitle,
    slugError,
    isSlugSaving,
  };
}
