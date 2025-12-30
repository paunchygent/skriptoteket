import type { DomainDiagnostic } from "./diagnostics";
import type { LinterContext } from "./linterContext";

export type LintRule = {
  id: string;
  check: (ctx: LinterContext) => DomainDiagnostic[];
};
