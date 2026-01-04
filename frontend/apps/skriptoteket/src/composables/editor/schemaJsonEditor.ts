import { lintGutter, linter, type Diagnostic } from "@codemirror/lint";
import type { Extension } from "@codemirror/state";

import { parseSchemaJsonArrayText } from "./schemaJsonHelpers";

type SchemaJsonPreset = {
  id: string;
  label: string;
  description: string;
  guidance: string[];
  example: unknown[];
};

const settingsSchemaExample: unknown[] = [
  { name: "theme_color", label: "Färgtema", kind: "string" },
  { name: "include_summary", label: "Inkludera sammanfattning", kind: "boolean" },
];

export const inputSchemaPresets: SchemaJsonPreset[] = [
  {
    id: "basic-text",
    label: "Textfält",
    description: "Ett enkelt textfält (string).",
    guidance: ["Fält visas innan körning.", "Lägg till fler fält vid behov."],
    example: [{ name: "title", label: "Titel", kind: "string" }],
  },
  {
    id: "file-optional",
    label: "Fil (valfri)",
    description: "En fil är valfri.",
    guidance: [
      "Filfält kräver min/max. min=0 gör fil valfri.",
      "Servern har globala gränser för antal/bytes.",
    ],
    example: [{ name: "files", label: "Filer", kind: "file", min: 0, max: 1 }],
  },
  {
    id: "file-required",
    label: "Fil (krävs)",
    description: "En fil är obligatorisk.",
    guidance: [
      "min=1 gör fil obligatorisk; max styr antal för verktyget.",
      "Servern har globala gränser för antal/bytes.",
    ],
    example: [{ name: "files", label: "Filer", kind: "file", min: 1, max: 1 }],
  },
];

function resolveInputPreset(presetId: string): SchemaJsonPreset {
  return inputSchemaPresets.find((preset) => preset.id === presetId) ?? inputSchemaPresets[0];
}

function formatSchemaSnippet(schema: unknown[]): string {
  return JSON.stringify(schema, null, 2);
}

export function schemaTextHasContent(text: string): boolean {
  return text.trim().length > 0;
}

export function buildSettingsSchemaSnippetText(): string {
  return formatSchemaSnippet(settingsSchemaExample);
}

export function buildInputSchemaSnippetText(presetId: string): string {
  const preset = resolveInputPreset(presetId);
  return formatSchemaSnippet(preset.example);
}

export function prettifySchemaJsonText(
  text: string,
  label: string,
  emptyValue: unknown[] | null,
): { text: string | null; error: string | null } {
  if (!schemaTextHasContent(text)) {
    return { text: null, error: null };
  }

  const parsed = parseSchemaJsonArrayText<unknown>(text, label, emptyValue);
  if (parsed.error || !parsed.value) {
    return { text: null, error: parsed.error ?? "Kunde inte tolka JSON." };
  }

  return { text: JSON.stringify(parsed.value, null, 2), error: null };
}

export function schemaJsonEditorExtensions(options: {
  label: string;
  emptyValue: unknown[] | null;
}): Extension[] {
  return [
    lintGutter(),
    linter((view) => {
      const text = view.state.doc.toString();
      const result = parseSchemaJsonArrayText<unknown>(text, options.label, options.emptyValue);

      if (!result.error) {
        return [];
      }

      const length = view.state.doc.length;
      if (length === 0) {
        return [];
      }

      const offset = result.errorDetails?.offset ?? 0;
      const from = Math.max(0, Math.min(offset, length - 1));
      const to = Math.min(from + 1, length);

      const diagnostic: Diagnostic = {
        from,
        to,
        severity: "error",
        message: result.error,
      };

      return [diagnostic];
    }),
  ];
}
