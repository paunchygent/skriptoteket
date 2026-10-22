/**
 * Purpose:
 *   Serialize a JSON value with object keys in sorted order, so two values
 *   that differ only in key order produce the same string.
 *
 * Relationships:
 *   - Consumed by the Klassrumskartan guest fingerprints, which must not
 *     change with key order, and by the exam rich-text editor, which compares
 *     the body it emitted with the body that comes back from a save.
 */

export function stableJson(value: unknown): string {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }

  if (Array.isArray(value)) {
    return `[${value.map((entry) => stableJson(entry)).join(",")}]`;
  }

  const entries = Object.entries(value).sort(([left], [right]) => {
    return left.localeCompare(right);
  });
  const serializedEntries = entries.map(([key, entryValue]) => {
    return `${JSON.stringify(key)}:${stableJson(entryValue)}`;
  });
  return `{${serializedEntries.join(",")}}`;
}
