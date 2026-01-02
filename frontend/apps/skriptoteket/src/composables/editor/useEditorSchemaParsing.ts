import { computed, type Ref } from "vue";

import type { components } from "../../api/openapi";
import { parseSchemaJsonArrayText } from "./schemaJsonHelpers";

type CreateDraftVersionRequest = components["schemas"]["CreateDraftVersionRequest"];
type ToolInputSchema = NonNullable<CreateDraftVersionRequest["input_schema"]>;
type ToolSettingsSchema = NonNullable<CreateDraftVersionRequest["settings_schema"]>;

type UseEditorSchemaParsingOptions = {
  inputSchemaText: Ref<string>;
  settingsSchemaText: Ref<string>;
};

export function useEditorSchemaParsing({
  inputSchemaText,
  settingsSchemaText,
}: UseEditorSchemaParsingOptions) {
  const inputSchemaResult = computed(() =>
    parseSchemaJsonArrayText<ToolInputSchema[number]>(
      inputSchemaText.value,
      "Indata-schemat",
      [],
    )
  );
  const settingsSchemaResult = computed(() =>
    parseSchemaJsonArrayText<ToolSettingsSchema[number]>(
      settingsSchemaText.value,
      "Inställningsschemat",
      null,
    )
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
