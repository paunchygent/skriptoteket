import { computed, onScopeDispose, ref, watch, type Ref } from "vue";

import { apiPost, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";

type SchemaValidationIssue = components["schemas"]["SchemaValidationIssue"];
type ValidateToolSchemasResponse = components["schemas"]["ValidateToolSchemasResponse"];

export type SchemaIssuesBySchema = {
  settings_schema: SchemaValidationIssue[];
  input_schema: SchemaValidationIssue[];
};

type UseEditorSchemaValidationOptions = {
  toolId: Readonly<Ref<string>>;
  inputSchema: Readonly<Ref<unknown>>;
  settingsSchema: Readonly<Ref<unknown | null>>;
  inputSchemaError: Readonly<Ref<string | null>>;
  settingsSchemaError: Readonly<Ref<string | null>>;
  isReadOnly: Readonly<Ref<boolean>>;
  debounceMs?: number;
};

export function useEditorSchemaValidation({
  toolId,
  inputSchema,
  settingsSchema,
  inputSchemaError,
  settingsSchemaError,
  isReadOnly,
  debounceMs = 800,
}: UseEditorSchemaValidationOptions) {
  const issues = ref<SchemaValidationIssue[]>([]);
  const isValidating = ref(false);
  const validationError = ref<string | null>(null);

  const hasParseErrors = computed(() => Boolean(inputSchemaError.value || settingsSchemaError.value));

  const canValidate = computed(() => {
    return toolId.value !== "" && !isReadOnly.value && !hasParseErrors.value;
  });

  const issuesBySchema = computed<SchemaIssuesBySchema>(() => {
    const grouped: SchemaIssuesBySchema = { settings_schema: [], input_schema: [] };
    for (const issue of issues.value) {
      if (issue.schema === "settings_schema") {
        grouped.settings_schema.push(issue);
      } else if (issue.schema === "input_schema") {
        grouped.input_schema.push(issue);
      }
    }
    return grouped;
  });

  const hasBlockingIssues = computed(() => issues.value.length > 0);

  let debounceTimerId: number | null = null;
  let requestSeq = 0;
  let latestSeq = 0;

  function clearDebounceTimer(): void {
    if (debounceTimerId !== null) {
      window.clearTimeout(debounceTimerId);
      debounceTimerId = null;
    }
  }

  function clearIssues(): void {
    latestSeq = requestSeq + 1;
    issues.value = [];
    validationError.value = null;
    isValidating.value = false;
  }

  async function runValidation(): Promise<boolean> {
    if (!canValidate.value) {
      clearIssues();
      return false;
    }

    const seq = (requestSeq += 1);
    latestSeq = seq;
    isValidating.value = true;
    validationError.value = null;

    try {
      const response = await apiPost<ValidateToolSchemasResponse>(
        `/api/v1/editor/tools/${encodeURIComponent(toolId.value)}/validate-schemas`,
        {
          settings_schema: settingsSchema.value ?? null,
          input_schema: inputSchema.value ?? null,
        },
      );

      if (latestSeq !== seq) {
        return false;
      }

      issues.value = response.issues ?? [];
      return response.valid;
    } catch (error: unknown) {
      if (latestSeq !== seq) {
        return false;
      }

      issues.value = [];

      if (isApiError(error)) {
        validationError.value = error.message;
      } else if (error instanceof Error) {
        validationError.value = error.message;
      } else {
        validationError.value = "Det gick inte att validera scheman.";
      }

      return false;
    } finally {
      if (latestSeq === seq) {
        isValidating.value = false;
      }
    }
  }

  async function validateNow(): Promise<boolean> {
    clearDebounceTimer();
    return await runValidation();
  }

  function scheduleValidation(): void {
    clearDebounceTimer();
    if (!canValidate.value) {
      clearIssues();
      return;
    }

    debounceTimerId = window.setTimeout(() => {
      void runValidation();
    }, debounceMs);
  }

  watch(
    [toolId, inputSchema, settingsSchema, inputSchemaError, settingsSchemaError, isReadOnly],
    scheduleValidation,
    { immediate: true },
  );

  onScopeDispose(() => {
    clearDebounceTimer();
  });

  return {
    issuesBySchema,
    hasBlockingIssues,
    isValidating,
    validationError,
    validateNow,
  };
}
