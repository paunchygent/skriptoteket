import type { LintRule } from "../lintRule";

import { BestPracticesRule } from "./bestPracticesRule";
import { ContractRule } from "./contractRule";
import { createEntrypointRule } from "./entrypointRule";
import { SecurityRule } from "./securityRule";
import { SyntaxRule } from "./syntaxRule";

export function createDefaultLintRules(opts: { entrypointName: string }): readonly LintRule[] {
  return [SyntaxRule, createEntrypointRule(opts.entrypointName), ContractRule, BestPracticesRule, SecurityRule];
}
