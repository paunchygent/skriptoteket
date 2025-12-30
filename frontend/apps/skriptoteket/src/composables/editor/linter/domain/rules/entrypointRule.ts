import type { DomainDiagnostic } from "../diagnostics";
import type { FixIntent } from "../fixIntents";
import type { LintRule } from "../lintRule";

const ST_ENTRYPOINT_MISSING = "ST_ENTRYPOINT_MISSING";

const FIX_CREATE_ENTRYPOINT = "Skapa startfunktion";

export function createEntrypointRule(entrypointName: string): LintRule {
  const resolvedEntrypointName = entrypointName.trim() || "run_tool";

  function entrypointDiagnostics(ctx: { text: string; facts: { entrypoint: { nameFrom: number; nameTo: number; params: string[] } | null } }): DomainDiagnostic[] {
    const match = ctx.facts.entrypoint;

    if (!match) {
      const expectedSignature = `def ${resolvedEntrypointName}(input_dir, output_dir)`;
      const stub = `def ${resolvedEntrypointName}(input_dir, output_dir):\n    return {"outputs": [], "next_actions": [], "state": {}}\n`;
      const prefix =
        ctx.text.trim().length === 0 ? "" : ctx.text.endsWith("\n\n") ? "" : ctx.text.endsWith("\n") ? "\n" : "\n\n";

      const fix: FixIntent = {
        kind: "insertText",
        label: FIX_CREATE_ENTRYPOINT,
        at: ctx.text.length,
        text: `${prefix}${stub}`,
      };

      return [
        {
          from: 0,
          to: Math.min(1, ctx.text.length),
          severity: "warning",
          source: ST_ENTRYPOINT_MISSING,
          message: `Saknar startfunktion: \`${expectedSignature}\``,
          fixes: [fix],
        },
      ];
    }

    const first = match.params[0] ?? null;
    const second = match.params[1] ?? null;
    if (first !== "input_dir" || second !== "output_dir") {
      return [
        {
          from: match.nameFrom,
          to: match.nameTo,
          severity: "warning",
          source: "ST_ENTRYPOINT",
          message: "Startfunktionen ska ta emot `input_dir` och `output_dir`.",
        },
      ];
    }

    return [];
  }

  return { id: "ST_ENTRYPOINT", check: entrypointDiagnostics };
}
