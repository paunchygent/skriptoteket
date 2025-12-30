import type { LinterContext } from "../linterContext";
import type { PythonNodeRange } from "../pythonFacts";

export function parsePythonStringLiteralValue(raw: string): string | null {
  if (raw.length < 2) return null;

  const quote = raw[0];
  if (quote !== "'" && quote !== '"') return null;
  if (raw[raw.length - 1] !== quote) return null;

  return raw.slice(1, -1);
}

export function stringLiteralValue(ctx: Pick<LinterContext, "text">, node: PythonNodeRange | null): string | null {
  if (!node || node.name !== "String") return null;
  return parsePythonStringLiteralValue(ctx.text.slice(node.from, node.to));
}
