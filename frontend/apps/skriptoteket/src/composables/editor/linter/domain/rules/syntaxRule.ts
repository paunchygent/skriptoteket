import type { LintRule } from "../lintRule";

export const SyntaxRule: LintRule = {
  id: "ST_SYNTAX_ERROR",
  check(ctx) {
    return ctx.facts.syntaxErrors;
  },
};
