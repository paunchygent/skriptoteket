import { computed, ref, watch, type Ref } from "vue";

import type { components } from "../../api/openapi";

type ToolMetadataResponse = components["schemas"]["ToolMetadataResponse"];
type JsonValue = components["schemas"]["JsonValue"];

type ToolInputSchema = NonNullable<ToolMetadataResponse["input_schema"]>;
type ToolInputField = ToolInputSchema[number];
type ToolInputFieldKind = ToolInputField["kind"];

type ToolInputFileField = Extract<ToolInputField, { kind: "file" }>;

export type ToolInputFormValue = string | boolean;
export type ToolInputFormValues = Record<string, ToolInputFormValue>;

type UseToolInputsOptions = {
  schema: Readonly<Ref<ToolMetadataResponse["input_schema"] | null | undefined>>;
  selectedFiles: Ref<File[]>;
};

function defaultValueForKind(kind: ToolInputFieldKind): ToolInputFormValue {
  switch (kind) {
    case "boolean":
      return false;
    default:
      return "";
  }
}

function isNonFileField(field: ToolInputField): boolean {
  return field.kind !== "file";
}

export function useToolInputs({ schema, selectedFiles }: UseToolInputsOptions) {
  const values = ref<ToolInputFormValues>({});

  const hasSchema = computed(() => schema.value !== null && schema.value !== undefined);

  const nonFileFields = computed<ToolInputField[]>(() => {
    const s = schema.value;
    if (!s) return [];
    return s.filter(isNonFileField);
  });

  const fileField = computed<ToolInputFileField | null>(() => {
    const s = schema.value;
    if (!s) return null;
    const field = s.find((candidate) => candidate.kind === "file") ?? null;
    return field as ToolInputFileField | null;
  });

  const fileAccept = computed(() => {
    const accept = fileField.value?.accept ?? null;
    if (!accept || accept.length === 0) return undefined;
    return accept.join(",");
  });

  const fileLabel = computed(() => fileField.value?.label ?? "Filer");
  const fileMultiple = computed(() => {
    // Legacy flow (no input_schema) uses the multi-file picker.
    if (!hasSchema.value) return true;
    return (fileField.value?.max ?? 1) > 1;
  });

  const showFilePicker = computed(() => !hasSchema.value || fileField.value !== null);

  const fileError = computed<string | null>(() => {
    if (!hasSchema.value) return null;

    if (fileField.value === null) {
      if (selectedFiles.value.length > 0) {
        return "Det här verktyget tar inte emot filer.";
      }
      return null;
    }

    const min = fileField.value.min;
    const max = fileField.value.max;
    const count = selectedFiles.value.length;

    if (count < min) {
      return min === 1 ? "Välj minst en fil." : `Välj minst ${min} filer.`;
    }
    if (count > max) {
      return max === 1 ? "Du kan välja max 1 fil." : `Du kan välja max ${max} filer.`;
    }
    return null;
  });

  const fieldErrors = computed<Record<string, string>>(() => {
    const errors: Record<string, string> = {};
    if (!hasSchema.value) return errors;

    for (const field of nonFileFields.value) {
      const raw = values.value[field.name] ?? defaultValueForKind(field.kind);

      if (field.kind === "integer") {
        const value = typeof raw === "string" ? raw.trim() : "";
        if (!value) continue;
        const parsed = Number.parseInt(value, 10);
        if (Number.isNaN(parsed)) {
          errors[field.name] = "Ogiltigt heltal.";
        }
        continue;
      }

      if (field.kind === "number") {
        const value = typeof raw === "string" ? raw.trim() : "";
        if (!value) continue;
        const parsed = Number.parseFloat(value);
        if (Number.isNaN(parsed)) {
          errors[field.name] = "Ogiltigt tal.";
        }
        continue;
      }

      if (field.kind === "enum") {
        const value = typeof raw === "string" ? raw.trim() : "";
        if (!value) continue;
        const options = new Set((field.options ?? []).map((opt) => opt.value));
        if (!options.has(value)) {
          errors[field.name] = "Ogiltigt val.";
        }
        continue;
      }
    }

    return errors;
  });

  const isValid = computed(() => {
    return fileError.value === null && Object.keys(fieldErrors.value).length === 0;
  });

  function resetValues(): void {
    if (!hasSchema.value) {
      values.value = {};
      return;
    }
    const next: ToolInputFormValues = {};
    for (const field of nonFileFields.value) {
      next[field.name] = defaultValueForKind(field.kind);
    }
    values.value = next;
  }

  function buildApiValues(): Record<string, JsonValue> {
    if (!hasSchema.value) return {};

    const apiValues: Record<string, JsonValue> = {};

    for (const field of nonFileFields.value) {
      const raw = values.value[field.name] ?? defaultValueForKind(field.kind);

      if (field.kind === "boolean") {
        apiValues[field.name] = raw === true;
        continue;
      }

      const value = typeof raw === "string" ? raw.trim() : "";
      if (!value) continue;

      if (field.kind === "integer") {
        const parsed = Number.parseInt(value, 10);
        if (Number.isNaN(parsed)) {
          throw new Error("Ogiltigt heltal.");
        }
        apiValues[field.name] = parsed;
        continue;
      }

      if (field.kind === "number") {
        const parsed = Number.parseFloat(value);
        if (Number.isNaN(parsed)) {
          throw new Error("Ogiltigt tal.");
        }
        apiValues[field.name] = parsed;
        continue;
      }

      apiValues[field.name] = value;
    }

    return apiValues;
  }

  watch(
    () => schema.value,
    () => {
      resetValues();
    },
    { immediate: true },
  );

  return {
    values,
    hasSchema,
    nonFileFields,
    fileField,
    fileAccept,
    fileLabel,
    fileMultiple,
    showFilePicker,
    fileError,
    fieldErrors,
    isValid,
    resetValues,
    buildApiValues,
  };
}
