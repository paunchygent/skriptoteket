export const VIRTUAL_FILE_IDS = [
  "tool.py",
  "entrypoint.txt",
  "settings_schema.json",
  "input_schema.json",
  "usage_instructions.md",
] as const;

export type VirtualFileId = (typeof VIRTUAL_FILE_IDS)[number];

export const VIRTUAL_DIFF_FILE_IDS = [
  "tool.py",
  "settings_schema.json",
  "input_schema.json",
  "usage_instructions.md",
] as const satisfies readonly VirtualFileId[];

export type VirtualFileLanguage = "python" | "json" | "text";

export type VirtualFileMeta = {
  id: VirtualFileId;
  label: string;
  language: VirtualFileLanguage;
};

export const VIRTUAL_FILES: readonly VirtualFileMeta[] = [
  { id: "tool.py", label: "Källkod", language: "python" },
  { id: "entrypoint.txt", label: "Entrypoint", language: "text" },
  { id: "settings_schema.json", label: "Inställningar (schema)", language: "json" },
  { id: "input_schema.json", label: "Indata (schema)", language: "json" },
  { id: "usage_instructions.md", label: "Instruktioner", language: "text" },
] as const;

export function isVirtualFileId(value: unknown): value is VirtualFileId {
  return typeof value === "string" && (VIRTUAL_FILE_IDS as readonly string[]).includes(value);
}

export type VirtualFileTextMap = Record<VirtualFileId, string>;

export type EditorVirtualFileTextFields = {
  entrypoint: string;
  sourceCode: string;
  settingsSchemaText: string;
  inputSchemaText: string;
  usageInstructions: string;
};

export function virtualFileTextFromEditorFields(
  fields: EditorVirtualFileTextFields,
): VirtualFileTextMap {
  return {
    "tool.py": fields.sourceCode,
    "entrypoint.txt": fields.entrypoint,
    "settings_schema.json": fields.settingsSchemaText,
    "input_schema.json": fields.inputSchemaText,
    "usage_instructions.md": fields.usageInstructions,
  };
}

type JsonSchema = unknown[] | null | undefined;

export type EditorBootVirtualFileFields = {
  entrypoint: string;
  source_code: string;
  settings_schema?: JsonSchema;
  input_schema?: JsonSchema;
  usage_instructions?: string | null;
};

function stringifySchema(schema: JsonSchema, emptyValue: string): string {
  if (schema === null || schema === undefined) return emptyValue;
  return JSON.stringify(schema, null, 2);
}

export function virtualFileTextFromEditorBoot(fields: EditorBootVirtualFileFields): VirtualFileTextMap {
  return {
    "tool.py": fields.source_code,
    "entrypoint.txt": fields.entrypoint,
    "settings_schema.json": stringifySchema(fields.settings_schema, ""),
    "input_schema.json": stringifySchema(fields.input_schema, ""),
    "usage_instructions.md": fields.usage_instructions ?? "",
  };
}

export function virtualFileLabel(id: VirtualFileId): string {
  return VIRTUAL_FILES.find((file) => file.id === id)?.label ?? id;
}

export function virtualFileLanguage(id: VirtualFileId): VirtualFileLanguage {
  return VIRTUAL_FILES.find((file) => file.id === id)?.language ?? "text";
}
