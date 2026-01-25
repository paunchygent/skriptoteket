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

export type FileSelectionMode = "upload" | "refs";
export type FileFieldSelection = {
  mode: FileSelectionMode;
  uploads: File[];
  refs: string[];
};

export type FileFieldSelections = Record<string, FileFieldSelection>;

export type ToolFileFieldSpec = {
  name: string;
  label: string;
  min: number;
  max: number;
  accept?: string[] | null;
};

type UseToolInputsOptions = {
  schema: Readonly<Ref<ToolMetadataResponse["input_schema"] | null | undefined>>;
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

function isFileField(field: ToolInputField): field is ToolInputFileField {
  return field.kind === "file";
}

function toFileSpec(field: ToolInputFileField): ToolFileFieldSpec {
  return {
    name: field.name,
    label: field.label,
    min: field.min,
    max: field.max,
    accept: field.accept ?? null,
  };
}

function defaultFileSelection(): FileFieldSelection {
  return { mode: "upload", uploads: [], refs: [] };
}

export function useToolInputs({ schema }: UseToolInputsOptions) {
  const values = ref<ToolInputFormValues>({});
  const fileSelections = ref<FileFieldSelections>({});

  const resolvedSchema = computed((): ToolInputSchema => schema.value ?? []);

  const nonFileFields = computed<ToolInputField[]>(() => {
    return resolvedSchema.value.filter(isNonFileField);
  });

  const fileFields = computed<ToolFileFieldSpec[]>(() => {
    return resolvedSchema.value.filter(isFileField).map(toFileSpec);
  });

  const fieldErrors = computed<Record<string, string>>(() => {
    const errors: Record<string, string> = {};
    for (const field of nonFileFields.value) {
      const raw = values.value[field.name];
      const value = typeof raw === "string" ? raw.trim() : "";
      if (!value) continue;

      if (field.kind === "integer") {
        const parsed = Number.parseInt(value, 10);
        if (Number.isNaN(parsed)) {
          errors[field.name] = "Ogiltigt heltal.";
        }
        continue;
      }

      if (field.kind === "number") {
        const parsed = Number.parseFloat(value);
        if (Number.isNaN(parsed)) {
          errors[field.name] = "Ogiltigt tal.";
        }
      }
    }
    return errors;
  });

  const fileAcceptByField = computed<Record<string, string | undefined>>(() => {
    const acceptByField: Record<string, string | undefined> = {};
    for (const field of fileFields.value) {
      if (field.accept && field.accept.length > 0) {
        acceptByField[field.name] = field.accept.join(",");
      } else {
        acceptByField[field.name] = undefined;
      }
    }
    return acceptByField;
  });

  const fileErrors = computed<Record<string, string | null>>(() => {
    const errors: Record<string, string | null> = {};
    for (const field of fileFields.value) {
      const selection = fileSelections.value[field.name] ?? defaultFileSelection();
      const count = selection.mode === "upload" ? selection.uploads.length : selection.refs.length;
      if (count < field.min) {
        errors[field.name] = field.min === 1 ? "Välj minst en fil." : `Välj minst ${field.min} filer.`;
        continue;
      }
      if (count > field.max) {
        errors[field.name] = field.max === 1 ? "Du kan välja max 1 fil." : `Du kan välja max ${field.max} filer.`;
        continue;
      }
      errors[field.name] = null;
    }
    return errors;
  });

  const hasFileSelections = computed(() => {
    return Object.values(fileSelections.value).some(
      (selection) => selection.uploads.length > 0 || selection.refs.length > 0,
    );
  });

  function ensureDefaults(): void {
    const next: ToolInputFormValues = {};
    for (const field of nonFileFields.value) {
      next[field.name] = defaultValueForKind(field.kind);
    }
    values.value = next;
  }

  function ensureFileSelections(): void {
    const next: FileFieldSelections = {};
    for (const field of fileFields.value) {
      const existing = fileSelections.value[field.name];
      next[field.name] = existing ?? defaultFileSelection();
    }
    fileSelections.value = next;
  }

  function resetValues(): void {
    ensureDefaults();
  }

  function resetFileSelections(): void {
    fileSelections.value = {};
    ensureFileSelections();
  }

  function setFileMode(fieldName: string, mode: FileSelectionMode): void {
    const current = fileSelections.value[fieldName] ?? defaultFileSelection();
    fileSelections.value = {
      ...fileSelections.value,
      [fieldName]: {
        mode,
        uploads: mode === "upload" ? current.uploads : [],
        refs: mode === "refs" ? current.refs : [],
      },
    };
  }

  function setFileUploads(fieldName: string, uploads: File[]): void {
    fileSelections.value = {
      ...fileSelections.value,
      [fieldName]: {
        mode: "upload",
        uploads,
        refs: [],
      },
    };
  }

  function setFileRefs(fieldName: string, refs: string[]): void {
    fileSelections.value = {
      ...fileSelections.value,
      [fieldName]: {
        mode: "refs",
        uploads: [],
        refs,
      },
    };
  }

  function buildApiValues(): Record<string, JsonValue> {
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
      ensureDefaults();
      ensureFileSelections();
    },
    { immediate: true },
  );

  return {
    values,
    nonFileFields,
    fieldErrors,
    fileFields,
    fileSelections,
    fileAcceptByField,
    fileErrors,
    hasFileSelections,
    resetValues,
    resetFileSelections,
    setFileMode,
    setFileUploads,
    setFileRefs,
    buildApiValues,
  };
}
