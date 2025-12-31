import { describe, expect, it } from "vitest";
import { syntaxTree } from "@codemirror/language";

import { createEntrypointRule } from "./domain/rules/entrypointRule";
import { SyntaxRule } from "./domain/rules/syntaxRule";
import { lookupVariable, type ScopeNode } from "./domain/variables";
import { buildScopedVariableTable } from "./infra/pythonVariables";
import { createPythonEditorState, buildHeadlessLinterContext, runHeadlessLintRule, runHeadlessLinter } from "../../../test/headlessLinterHarness";

function requireScope(scopes: readonly ScopeNode[], match: (scope: ScopeNode) => boolean, label: string): ScopeNode {
  const found = scopes.find(match) ?? null;
  if (!found) throw new Error(`Expected to find scope: ${label}`);
  return found;
}

function scopeHeader(state: { doc: { sliceString: (from: number, to: number) => string } }, scope: ScopeNode): string {
  const chunk = state.doc.sliceString(scope.from, Math.min(scope.from + 200, scope.to));
  const newline = chunk.indexOf("\n");
  return newline === -1 ? chunk : chunk.slice(0, newline);
}

describe("headless linter test harness", () => {
  it("evaluates a rule headlessly (no EditorView/DOM)", () => {
    const doc = `
def other(input_dir, output_dir):
    return {}
`;

    const rule = createEntrypointRule("run_tool");
    const diagnostics = runHeadlessLintRule(rule, doc, { entrypointName: "run_tool" });

    expect(diagnostics.some((diagnostic) => diagnostic.source === "ST_ENTRYPOINT_MISSING")).toBe(true);
    expect(diagnostics.some((diagnostic) => diagnostic.source === "ST_SYNTAX_ERROR")).toBe(false);
  });

  it("maps Lezer error nodes to ST_SYNTAX_ERROR diagnostics via buildLinterContext", () => {
    const doc = `
def run_tool(input_dir, output_dir)
    return {"outputs": []}
`;

    const ctx = buildHeadlessLinterContext(doc, { entrypointName: "run_tool" });

    expect(ctx.facts.syntaxErrors.length).toBeGreaterThan(0);
    expect(ctx.facts.syntaxErrors.every((diagnostic) => diagnostic.source === "ST_SYNTAX_ERROR")).toBe(true);
    expect(ctx.facts.syntaxErrors.every((diagnostic) => diagnostic.severity === "error")).toBe(true);
    expect(ctx.facts.syntaxErrors.every((diagnostic) => diagnostic.message.includes("Syntaxfel"))).toBe(true);

    const docLength = doc.length;
    for (const diagnostic of ctx.facts.syntaxErrors) {
      expect(diagnostic.from).toBeGreaterThanOrEqual(0);
      expect(diagnostic.to).toBeGreaterThan(diagnostic.from);
      expect(diagnostic.to).toBeLessThanOrEqual(docLength);
    }

    const ruleDiagnostics = runHeadlessLintRule(SyntaxRule, doc, { entrypointName: "run_tool" });
    expect(ruleDiagnostics).toEqual(ctx.facts.syntaxErrors);

    const linterDiagnostics = runHeadlessLinter(doc, { entrypointName: "run_tool" });
    expect(linterDiagnostics.length).toBeGreaterThan(0);
    expect(linterDiagnostics.every((diagnostic) => diagnostic.source === "ST_SYNTAX_ERROR")).toBe(true);
  });

  it("resolves shadowed variables correctly across nested function scopes", () => {
    const doc = `
x = []

def outer():
    x = {}
    x.update({"a": 1})

    def inner():
        x = []
        x.append(1)
        return x

    return inner()
`;

    const state = createPythonEditorState(doc);
    const { chain, moduleScope, scopes } = buildScopedVariableTable(state, syntaxTree(state));

    const outerScope = requireScope(
      scopes,
      (scope) => scope.kind === "function" && scopeHeader(state, scope).includes("def outer"),
      "outer()",
    );
    const innerScope = requireScope(
      scopes,
      (scope) => scope.kind === "function" && scopeHeader(state, scope).includes("def inner"),
      "inner()",
    );

    expect(innerScope.parent).toBe(outerScope);

    const moduleX = lookupVariable(chain, "x", moduleScope);
    const outerX = lookupVariable(chain, "x", outerScope);
    const innerX = lookupVariable(chain, "x", innerScope);

    expect(moduleX?.type).toBe("List");
    expect(outerX?.type).toBe("Dict");
    expect(innerX?.type).toBe("List");

    expect(outerX?.operations).toContain("update");
    expect(innerX?.operations).toContain("append");
    expect(moduleX?.operations ?? []).not.toContain("append");
    expect(moduleX?.operations ?? []).not.toContain("update");
  });
});
