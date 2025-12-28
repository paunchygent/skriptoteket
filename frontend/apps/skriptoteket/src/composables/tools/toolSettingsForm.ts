import type { components } from "../../api/openapi";

type ToolSettingsResponse = components["schemas"]["ToolSettingsResponse"];
export type SettingsField = NonNullable<ToolSettingsResponse["settings_schema"]>[number];
type SettingsFieldKind = SettingsField["kind"];
type JsonValue = components["schemas"]["JsonValue"];

export type FieldValue = string | boolean | string[];
export type SettingsFormValues = Record<string, FieldValue>;

export function defaultValueForKind(kind: SettingsFieldKind): FieldValue {
  switch (kind) {
    case "boolean":
      return false;
    case "multi_enum":
      return [];
    default:
      return "";
  }
}

export function toFormValue(kind: SettingsFieldKind, raw: JsonValue | undefined): FieldValue {
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

export function toApiValue(kind: SettingsFieldKind, raw: FieldValue): JsonValue | undefined {
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

export function buildApiValues(
  schema: SettingsField[],
  formValues: SettingsFormValues,
): Record<string, JsonValue> {
  const values: Record<string, JsonValue> = {};

  for (const field of schema) {
    const raw = formValues[field.name] ?? defaultValueForKind(field.kind);
    const converted = toApiValue(field.kind, raw);
    if (converted === undefined) continue;
    values[field.name] = converted;
  }

  return values;
}

export function buildFormValues(
  schema: SettingsField[],
  apiValues: ToolSettingsResponse["values"],
): SettingsFormValues {
  const values: SettingsFormValues = {};

  for (const field of schema) {
    values[field.name] = toFormValue(field.kind, apiValues[field.name]);
  }

  return values;
}
