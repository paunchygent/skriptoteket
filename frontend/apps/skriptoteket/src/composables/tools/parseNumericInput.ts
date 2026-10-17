export type NumericInputKind = "integer" | "number";

// Decimal notation, including fractions and exponents; never accept a numeric prefix.
const DECIMAL_NUMBER = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;

export function parseNumericInput(raw: string, kind: NumericInputKind): number | null {
  const value = raw.trim();
  if (!DECIMAL_NUMBER.test(value)) return null;

  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return null;
  if (kind === "integer" && !Number.isInteger(parsed)) return null;
  return parsed;
}
