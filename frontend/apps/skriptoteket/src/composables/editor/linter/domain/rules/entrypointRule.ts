import type { DomainDiagnostic } from "../diagnostics";
import type { LintRule } from "../lintRule";

const ST_ENTRYPOINT_MISSING = "ST_ENTRYPOINT_MISSING";

export function createEntrypointRule(entrypointName: string): LintRule {
  const resolvedEntrypointName = entrypointName.trim() || "run_tool";

  function entrypointDiagnostics(ctx: { text: string; facts: { entrypoint: { nameFrom: number; nameTo: number; params: string[] } | null } }): DomainDiagnostic[] {
    const match = ctx.facts.entrypoint;

    if (!match) {
      const expectedSignature = `def ${resolvedEntrypointName}(input_dir, output_dir)`;
      return [
        {
          from: 0,
          to: Math.min(1, ctx.text.length),
          severity: "warning",
          source: ST_ENTRYPOINT_MISSING,
          message: `Saknar startfunktion: \`${expectedSignature}\``,
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
