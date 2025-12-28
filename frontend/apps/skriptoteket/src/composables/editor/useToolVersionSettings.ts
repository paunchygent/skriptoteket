import { computed, ref, watch, type Ref } from "vue";

import { apiFetch, apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import {
  buildApiValues,
  buildFormValues,
  type SettingsField,
  type SettingsFormValues,
} from "../tools/toolSettingsForm";
import { useToast } from "../useToast";

type ToolSettingsResponse = components["schemas"]["ToolSettingsResponse"];
type JsonValue = components["schemas"]["JsonValue"];

type UseToolVersionSettingsOptions = {
  versionId: Readonly<Ref<string>>;
};

export function useToolVersionSettings({ versionId }: UseToolVersionSettingsOptions) {
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
    if (!versionId.value) {
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
        `/api/v1/editor/tool-versions/${encodeURIComponent(versionId.value)}/settings`,
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
    if (!versionId.value) return;
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
        `/api/v1/editor/tool-versions/${encodeURIComponent(versionId.value)}/settings`,
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
    () => versionId.value,
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

