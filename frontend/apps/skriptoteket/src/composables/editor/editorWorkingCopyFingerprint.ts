import type { EditorWorkingCopyFields } from "./editorPersistence";
import { bundleFilesFingerprint } from "./bundleFiles";

export function fieldsFingerprint(fields: EditorWorkingCopyFields): string {
  return [
    fields.entrypoint,
    fields.sourceCode,
    fields.settingsSchemaText,
    fields.inputSchemaText,
    fields.usageInstructions,
    bundleFilesFingerprint(fields.bundleFiles),
  ].join("\u0000");
}

export function areFieldsEqual(a: EditorWorkingCopyFields, b: EditorWorkingCopyFields): boolean {
  return fieldsFingerprint(a) === fieldsFingerprint(b);
}
