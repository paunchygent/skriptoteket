import { computed, ref, watch, type Ref } from "vue";

import { apiFetch, apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { useToast } from "../useToast";

type ToolSettingsResponse = components["schemas"]["ToolSettingsResponse"];
type SettingsField = NonNullable<ToolSettingsResponse["settings_schema"]>[number];
type SettingsFieldKind = SettingsField["kind"];
type JsonValue = components["schemas"]["JsonValue"];

type FieldValue = string | boolean | string[];
type SettingsFormValues = Record<string, FieldValue>;

type UseToolSettingsOptions = {
  toolId: Readonly<Ref<string>>;
};

function defaultValueForKind(kind: SettingsFieldKind): FieldValue {
  switch (kind) {
    case "boolean":
      return false;
    case "multi_enum":
      return [];
    default:
      return "";
  }
}

function toFormValue(kind: SettingsFieldKind, raw: JsonValue | undefined): FieldValue {
  if (kind === "boolean") {
    return raw === true;
  }

  if (kind === "multi_enum") {
    if (Array.isArray(raw) && raw.every((item) => typeof item === "string")) {
      return raw;
    }
    return [];
  }

  if (raw === null || raw === undefined) return "";
  if (typeof raw === "string") return raw;
  if (typeof raw === "number") return String(raw);
  if (typeof raw === "boolean") return raw ? "true" : "false";
  return "";
}

function toApiValue(kind: SettingsFieldKind, raw: FieldValue): JsonValue | undefined {
  if (kind === "boolean") {
    return Boolean(raw);
  }

  if (kind === "multi_enum") {
    return Array.isArray(raw) ? raw : [];
  }

  const value = typeof raw === "string" ? raw.trim() : "";

  if (kind === "integer") {
    if (!value) return undefined;
    const parsed = Number.parseInt(value, 10);
    if (Number.isNaN(parsed)) {
      throw new Error("Ogiltigt heltal.");
    }
    return parsed;
  }

  if (kind === "number") {
    if (!value) return undefined;
    const parsed = Number.parseFloat(value);
    if (Number.isNaN(parsed)) {
      throw new Error("Ogiltigt tal.");
    }
    return parsed;
  }

  if (!value) return undefined;
  return value;
}

function buildApiValues(schema: SettingsField[], formValues: SettingsFormValues): Record<string, JsonValue> {
  const values: Record<string, JsonValue> = {};

  for (const field of schema) {
    const raw = formValues[field.name] ?? defaultValueForKind(field.kind);
    const converted = toApiValue(field.kind, raw);
    if (converted === undefined) continue;
    values[field.name] = converted;
  }

  return values;
}

function buildFormValues(schema: SettingsField[], apiValues: ToolSettingsResponse["values"]): SettingsFormValues {
  const values: SettingsFormValues = {};

  for (const field of schema) {
    values[field.name] = toFormValue(field.kind, apiValues[field.name]);
  }

  return values;
}

export function useToolSettings({ toolId }: UseToolSettingsOptions) {
  const settingsSchema = ref<SettingsField[] | null>(null);
  const schemaVersion = ref<string | null>(null);
  const stateRev = ref<number | null>(null);
  const values = ref<SettingsFormValues>({});

  const toast = useToast();

  const isLoading = ref(false);
  const isSaving = ref(false);
  const errorMessage = ref<string | null>(null);

  const hasSchema = computed(() => (settingsSchema.value?.length ?? 0) > 0);

  async function loadSettings(): Promise<void> {
    if (!toolId.value) {
      settingsSchema.value = null;
      schemaVersion.value = null;
      stateRev.value = null;
      values.value = {};
      return;
    }

    isLoading.value = true;
    errorMessage.value = null;

    try {
      const response = await apiGet<ToolSettingsResponse>(
        `/api/v1/tools/${encodeURIComponent(toolId.value)}/settings`,
      );

      settingsSchema.value = response.settings_schema;
      schemaVersion.value = response.schema_version;
      stateRev.value = response.state_rev;

      if (response.settings_schema) {
        values.value = buildFormValues(response.settings_schema, response.values);
      } else {
        values.value = {};
      }
    } catch (error: unknown) {
      settingsSchema.value = null;
      schemaVersion.value = null;
      stateRev.value = null;
      values.value = {};
      if (isApiError(error)) {
        errorMessage.value = error.message;
      } else if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = "Det gick inte att ladda inställningarna.";
      }
    } finally {
      isLoading.value = false;
    }
  }

  async function saveSettings(): Promise<void> {
    if (!toolId.value) return;
    if (!settingsSchema.value) return;
    if (stateRev.value === null) {
      errorMessage.value = "Inställningarna är inte redo än. Ladda om sidan.";
      return;
    }
    if (isSaving.value) return;

    isSaving.value = true;
    errorMessage.value = null;

    try {
      let apiValues: Record<string, JsonValue>;
      try {
        apiValues = buildApiValues(settingsSchema.value, values.value);
      } catch (error: unknown) {
        if (error instanceof Error) {
          errorMessage.value = error.message;
        } else {
          errorMessage.value = "Det gick inte att spara inställningarna.";
        }
        return;
      }

      const response = await apiFetch<ToolSettingsResponse>(
        `/api/v1/tools/${encodeURIComponent(toolId.value)}/settings`,
        {
          method: "PUT",
          body: {
            expected_state_rev: stateRev.value,
            values: apiValues,
          },
        },
      );

      settingsSchema.value = response.settings_schema;
      schemaVersion.value = response.schema_version;
      stateRev.value = response.state_rev;
      values.value = response.settings_schema
        ? buildFormValues(response.settings_schema, response.values)
        : {};

      toast.success("Inställningar sparade.");
    } catch (error: unknown) {
      if (isApiError(error)) {
        const message =
          error.status === 409
            ? "Inställningarna har ändrats i en annan flik. Ladda om sidan och försök igen."
            : error.message;

        if (error.status === 409) {
          toast.warning(message);
        } else {
          toast.failure(message);
        }
      } else if (error instanceof Error) {
        toast.failure(error.message);
      } else {
        toast.failure("Det gick inte att spara inställningarna.");
      }
    } finally {
      isSaving.value = false;
    }
  }

  watch(
    () => toolId.value,
    () => {
      void loadSettings();
    },
    { immediate: true },
  );

  return {
    settingsSchema,
    schemaVersion,
    stateRev,
    values,
    hasSchema,
    isLoading,
    isSaving,
    errorMessage,
    loadSettings,
    saveSettings,
  };
}
