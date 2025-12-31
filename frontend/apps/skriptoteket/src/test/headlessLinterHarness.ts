import { EditorState } from "@codemirror/state";
import { python } from "@codemirror/lang-python";

import type { DomainDiagnostic } from "../composables/editor/linter/domain/diagnostics";
import type { LintRule } from "../composables/editor/linter/domain/lintRule";
import type { LinterContext } from "../composables/editor/linter/domain/linterContext";
import { createDefaultLintRules } from "../composables/editor/linter/domain/rules/defaultRuleSet";
import { buildLinterContext } from "../composables/editor/linter/infra/buildLinterContext";

export function createPythonEditorState(doc: string): EditorState {
  return EditorState.create({ doc, extensions: [python()] });
}

export function buildHeadlessLinterContext(doc: string, opts: { entrypointName: string }): LinterContext {
  return buildLinterContext(createPythonEditorState(doc), opts);
}

export function runHeadlessLintRule(rule: LintRule, doc: string, opts: { entrypointName: string }): DomainDiagnostic[] {
  const ctx = buildHeadlessLinterContext(doc, opts);
  return rule.check(ctx);
}

export function runHeadlessLinter(doc: string, opts: { entrypointName: string }): DomainDiagnostic[] {
  const ctx = buildHeadlessLinterContext(doc, opts);
  const rules = createDefaultLintRules({ entrypointName: opts.entrypointName });

  if (ctx.facts.syntaxErrors.length > 0) return ctx.facts.syntaxErrors;
  return rules.flatMap((rule) => rule.check(ctx));
}
