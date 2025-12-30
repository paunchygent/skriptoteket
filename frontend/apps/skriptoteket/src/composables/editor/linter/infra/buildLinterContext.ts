import type { EditorState } from "@codemirror/state";
import { syntaxTree } from "@codemirror/language";

import {
  extractPythonArrayElements,
  extractPythonDictionaryEntries,
  findPythonFunctionDefinitions,
  findPythonImportModules,
  findPythonMemberCalls,
  findPythonRaiseStatements,
  findPythonReturnStatements,
  findPythonSyntaxErrors,
} from "../../pythonLezer";

import type { DomainDiagnostic } from "../domain/diagnostics";
import type { LinterContext } from "../domain/linterContext";

import { buildPythonImportBindingsSnapshot, findPythonCallExpressions } from "./pythonAnalysis";
import { buildScopedVariableTable } from "./pythonVariables";

export function buildLinterContext(state: EditorState, opts: { entrypointName: string }): LinterContext {
  const tree = syntaxTree(state);
  const entrypointName = opts.entrypointName.trim() || "run_tool";
  const text = state.doc.toString();

  const syntaxErrors: DomainDiagnostic[] = findPythonSyntaxErrors(state, tree).map((diagnostic) => ({
    from: diagnostic.from,
    to: diagnostic.to,
    severity: diagnostic.severity,
    message: diagnostic.message,
    source: "ST_SYNTAX_ERROR",
  }));

  const imports = buildPythonImportBindingsSnapshot(state);
  const functions = findPythonFunctionDefinitions(state);
  const entrypoint = functions.find((def) => def.name === entrypointName) ?? null;

  const entrypointBodyRange =
    entrypoint && entrypoint.bodyFrom !== null && entrypoint.bodyTo !== null
      ? { from: entrypoint.bodyFrom, to: entrypoint.bodyTo }
      : null;

  const calls = entrypointBodyRange ? findPythonCallExpressions(state, entrypointBodyRange) : [];
  const returns = entrypointBodyRange ? findPythonReturnStatements(state, entrypointBodyRange) : [];
  const raises = entrypointBodyRange ? findPythonRaiseStatements(state, entrypointBodyRange) : [];

  const importModules = findPythonImportModules(state);
  const memberCalls = findPythonMemberCalls(state);

  const scopedVariables = buildScopedVariableTable(state, tree);

  return {
    text,
    facts: {
      syntaxErrors,
      imports,
      functions,
      entrypoint,
      calls,
      returns,
      raises,
      importModules,
      memberCalls,
      variables: scopedVariables.chain,
    },
    pythonLiterals: {
      dictionaryEntries: (dict) => extractPythonDictionaryEntries(state, dict),
      arrayElements: (array) => extractPythonArrayElements(state, array),
    },
  };
}
