export function parsePythonStringLiteralValue(raw: string): string | null {
  if (raw.length < 2) return null;

  const quote = raw[0];
  if (quote !== "'" && quote !== '"') return null;
  if (raw[raw.length - 1] !== quote) return null;

  return raw.slice(1, -1);
}
