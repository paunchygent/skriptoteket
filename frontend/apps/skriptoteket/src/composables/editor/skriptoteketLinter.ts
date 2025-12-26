import type { EditorState, Extension } from "@codemirror/state";
import { lintGutter, linter, type Diagnostic } from "@codemirror/lint";

import type { SkriptoteketIntelligenceConfig } from "./skriptoteketIntelligence";
import { SKRIPTOTEKET_CONTRACT_KEYS, SKRIPTOTEKET_NOTICE_LEVELS, SKRIPTOTEKET_OUTPUT_KINDS } from "./skriptoteketMetadata";
import {
  extractPythonArrayElements,
  extractPythonDictionaryEntries,
  findPythonFunctionDefinitions,
  findPythonImportModules,
  findPythonMemberCalls,
  findPythonReturnStatements,
  parsePythonStringLiteralValue,
  type PythonFunctionDefinition,
  type PythonNodeRange,
} from "./skriptoteketPythonTree";

export function skriptoteketLinter(config: SkriptoteketIntelligenceConfig): Extension {
  const entrypointName = config.entrypointName.trim() || "run_tool";

  function stringLiteralValue(state: EditorState, node: PythonNodeRange | null): string | null {
    if (!node || node.name !== "String") return null;
    return parsePythonStringLiteralValue(state.doc.sliceString(node.from, node.to));
  }

  function entrypointDiagnostics(state: EditorState, match: PythonFunctionDefinition | null): Diagnostic[] {

    if (!match) {
      const expectedSignature = `def ${entrypointName}(input_dir, output_dir)`;
      return [
        {
          from: 0,
          to: Math.min(1, state.doc.length),
          severity: "warning",
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
          message: "Startfunktionen ska ta emot `input_dir` och `output_dir`.",
        },
      ];
    }

    return [];
  }

  function contractDiagnostics(state: EditorState, match: PythonFunctionDefinition | null): Diagnostic[] {
    if (!match || match.bodyFrom === null || match.bodyTo === null) return [];

    const returns = findPythonReturnStatements(state, { from: match.bodyFrom, to: match.bodyTo });
    if (returns.length === 0) return [];

    const literalDictReturns = returns.filter((stmt) => stmt.expression?.name === "DictionaryExpression");
    const literalStringReturns = returns.filter((stmt) => stmt.expression?.name === "String");

    if (literalDictReturns.length === 0 && literalStringReturns.length === 0) {
      return [
        {
          from: match.nameFrom,
          to: match.nameTo,
          severity: "hint",
          message:
            "Kunde inte verifiera Contract v2 eftersom returvärdet byggs dynamiskt. Kontrollera att du returnerar dict med outputs/next_actions/state.",
        },
      ];
    }

    const diagnostics: Diagnostic[] = [];

    for (const stmt of literalDictReturns) {
      const dictNode = stmt.expression;
      if (!dictNode) continue;

      const entries = extractPythonDictionaryEntries(state, dictNode);
      const byKey = new Map(entries.map((entry) => [entry.key, entry]));

      const missingKeys = SKRIPTOTEKET_CONTRACT_KEYS.filter((key) => !byKey.has(key));
      if (missingKeys.length > 0) {
        diagnostics.push({
          from: dictNode.from,
          to: Math.min(dictNode.from + 1, state.doc.length),
          severity: "info",
          message: `Retur-dict saknar nycklar: ${missingKeys.join(" / ")}.`,
        });
      }

      const outputsEntry = byKey.get("outputs") ?? null;
      if (!outputsEntry) continue;

      const outputsValue = outputsEntry.value;
      if (!outputsValue || outputsValue.name !== "ArrayExpression") {
        diagnostics.push({
          from: outputsEntry.keyFrom,
          to: outputsEntry.keyTo,
          severity: "error",
          message: "`outputs` måste vara en lista (`[...]`).",
        });
        continue;
      }

      const outputEntries = extractPythonArrayElements(state, outputsValue).filter(
        (node) => node.name === "DictionaryExpression",
      );

      for (const outputDict of outputEntries) {
        const outputFields = extractPythonDictionaryEntries(state, outputDict);
        const outputByKey = new Map(outputFields.map((entry) => [entry.key, entry]));

        const kindEntry = outputByKey.get("kind") ?? null;
        const kindValue = stringLiteralValue(state, kindEntry?.value ?? null);
        if (!kindEntry || !kindValue) {
          diagnostics.push({
            from: outputDict.from,
            to: Math.min(outputDict.from + 1, state.doc.length),
            severity: "warning",
            message: 'Ett output-objekt saknar "kind".',
          });
          continue;
        }

        if (!SKRIPTOTEKET_OUTPUT_KINDS.includes(kindValue as (typeof SKRIPTOTEKET_OUTPUT_KINDS)[number])) {
          diagnostics.push({
            from: kindEntry.value?.from ?? outputDict.from,
            to: kindEntry.value?.to ?? Math.min(outputDict.from + 1, state.doc.length),
            severity: "warning",
            message: `Ogiltigt kind: "${kindValue}". Tillåtna: ${SKRIPTOTEKET_OUTPUT_KINDS.join(", ")}.`,
          });
          continue;
        }

        if (kindValue !== "notice") continue;

        const levelEntry = outputByKey.get("level") ?? null;
        const messageEntry = outputByKey.get("message") ?? null;
        if (!levelEntry || !messageEntry) {
          diagnostics.push({
            from: outputDict.from,
            to: Math.min(outputDict.from + 1, state.doc.length),
            severity: "warning",
            message: 'Notice saknar "level" eller "message".',
          });
          continue;
        }

        const levelValue = stringLiteralValue(state, levelEntry.value);
        if (
          levelValue &&
          !SKRIPTOTEKET_NOTICE_LEVELS.includes(levelValue as (typeof SKRIPTOTEKET_NOTICE_LEVELS)[number])
        ) {
          diagnostics.push({
            from: levelEntry.value?.from ?? outputDict.from,
            to: levelEntry.value?.to ?? Math.min(outputDict.from + 1, state.doc.length),
            severity: "warning",
            message: "Notice level måste vara info/warning/error.",
          });
        }
      }
    }

    return diagnostics;
  }

  function securityDiagnostics(state: EditorState): Diagnostic[] {
    const diagnostics: Diagnostic[] = [];

    const blockedNetworkModules = new Set(["aiohttp", "requests", "httpx", "urllib3"]);
    const imports = findPythonImportModules(state);
    for (const entry of imports) {
      if (blockedNetworkModules.has(entry.modulePath) || entry.modulePath === "urllib.request") {
        diagnostics.push({
          from: entry.from,
          to: entry.to,
          severity: "error",
          message: "Nätverksbibliotek stöds inte i sandbox (ingen nätverksåtkomst).",
        });
      }
    }

    const calls = findPythonMemberCalls(state);
    for (const call of calls) {
      const isSubprocessRun = call.objectName === "subprocess" && call.propertyName === "run";
      const isOsShell = call.objectName === "os" && (call.propertyName === "system" || call.propertyName === "popen");
      if (!isSubprocessRun && !isOsShell) continue;

      diagnostics.push({
        from: call.propertyFrom,
        to: call.propertyTo,
        severity: "warning",
        message: "Undvik subprocess/os.system i sandbox. Använd rena Python-lösningar.",
      });
    }

    return diagnostics;
  }

  return [
    lintGutter(),
    linter((view) => {
      const defs = findPythonFunctionDefinitions(view.state);
      const match = defs.find((def) => def.name === entrypointName) ?? null;
      return [
        ...entrypointDiagnostics(view.state, match),
        ...contractDiagnostics(view.state, match),
        ...securityDiagnostics(view.state),
      ];
    }),
  ];
}
