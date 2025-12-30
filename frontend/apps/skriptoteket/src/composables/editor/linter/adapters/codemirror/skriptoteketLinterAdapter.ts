import type { Extension } from "@codemirror/state";
import { lintGutter, linter, type Diagnostic } from "@codemirror/lint";

import type { SkriptoteketIntelligenceConfig } from "../../../skriptoteketIntelligence";

import type { DomainDiagnostic } from "../../domain/diagnostics";
import { createDefaultLintRules } from "../../domain/rules/defaultRuleSet";
import { buildLinterContext } from "../../infra/buildLinterContext";

function clampPos(pos: number, docLength: number): number {
  return Math.max(0, Math.min(pos, docLength));
}

function toCodeMirrorDiagnostic(domainDiagnostic: DomainDiagnostic): Diagnostic {
  const diagnostic: Diagnostic = {
    from: domainDiagnostic.from,
    to: domainDiagnostic.to,
    severity: domainDiagnostic.severity,
    source: domainDiagnostic.source,
    message: domainDiagnostic.message,
  };

  const fixes = domainDiagnostic.fixes ?? [];
  if (fixes.length === 0) return diagnostic;

  diagnostic.actions = fixes.map((fix) => ({
    name: fix.label,
    apply(view) {
      const docLength = view.state.doc.length;
      const doc = view.state.doc;

      if (fix.kind === "replaceRange") {
        const from = clampPos(fix.from, docLength);
        const to = clampPos(fix.to, docLength);
        if (doc.sliceString(from, to) === fix.insert) return;
        view.dispatch({ changes: { from, to, insert: fix.insert } });
      } else if (fix.kind === "insertText") {
        const at = clampPos(fix.at, docLength);
        if (doc.sliceString(at, at + fix.text.length) === fix.text) return;
        view.dispatch({ changes: { from: at, insert: fix.text } });
      } else if (fix.kind === "deleteRange") {
        const from = clampPos(fix.from, docLength);
        const to = clampPos(fix.to, docLength);
        if (from === to) return;
        view.dispatch({ changes: { from, to, insert: "" } });
      }
    },
  }));

  return diagnostic;
}

export function skriptoteketLinterAdapter(config: SkriptoteketIntelligenceConfig): Extension {
  const entrypointName = config.entrypointName.trim() || "run_tool";
  const rules = createDefaultLintRules({ entrypointName });

  return [
    lintGutter(),
    linter((view) => {
      const ctx = buildLinterContext(view.state, { entrypointName });

      if (ctx.facts.syntaxErrors.length > 0) {
        return ctx.facts.syntaxErrors.map(toCodeMirrorDiagnostic);
      }

      return rules.flatMap((rule) => rule.check(ctx)).map(toCodeMirrorDiagnostic);
    }),
  ];
}
