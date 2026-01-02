import { computed, type Ref } from "vue";

import type { components } from "../../api/openapi";

type CreateDraftVersionRequest = components["schemas"]["CreateDraftVersionRequest"];
type ToolInputSchema = NonNullable<CreateDraftVersionRequest["input_schema"]>;
type ToolSettingsSchema = NonNullable<CreateDraftVersionRequest["settings_schema"]>;

type SchemaParseResult<T> = {
  value: T | null;
  error: string | null;
};

function parseSchemaArray<T>(
  text: string,
  label: string,
  emptyValue: T[] | null,
): SchemaParseResult<T[]> {
  const trimmed = text.trim();
  if (!trimmed) {
    return { value: emptyValue, error: null };
  }

  try {
    const parsed = JSON.parse(trimmed);
    if (!Array.isArray(parsed)) {
      return { value: null, error: `${label} måste vara en JSON-array.` };
    }
    return { value: parsed as T[], error: null };
  } catch {
    return { value: null, error: `${label} måste vara giltig JSON.` };
  }
}

type UseEditorSchemaParsingOptions = {
  inputSchemaText: Ref<string>;
  settingsSchemaText: Ref<string>;
};

export function useEditorSchemaParsing({
  inputSchemaText,
  settingsSchemaText,
}: UseEditorSchemaParsingOptions) {
  const inputSchemaResult = computed(() =>
    parseSchemaArray<ToolInputSchema[number]>(inputSchemaText.value, "Indata-schemat", [])
  );
  const settingsSchemaResult = computed(() =>
    parseSchemaArray<ToolSettingsSchema[number]>(settingsSchemaText.value, "Inställningsschemat", null)
  );

  const inputSchema = computed(() => (inputSchemaResult.value.value ?? []) as ToolInputSchema);
  const inputSchemaError = computed(() => inputSchemaResult.value.error);

  const settingsSchema = computed(
    () => settingsSchemaResult.value.value as ToolSettingsSchema | null
  );
  const settingsSchemaError = computed(() => settingsSchemaResult.value.error);

  return {
    inputSchema,
    inputSchemaError,
    settingsSchema,
    settingsSchemaError,
  };
}
