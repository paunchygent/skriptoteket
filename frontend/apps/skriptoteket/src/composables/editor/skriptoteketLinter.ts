import type { EditorState, Extension } from "@codemirror/state";
import { lintGutter, linter, type Diagnostic } from "@codemirror/lint";

import type { SkriptoteketIntelligenceConfig } from "./skriptoteketIntelligence";
import {
  buildPythonImportBindingsSnapshot,
  findPythonCallExpressions,
  type PythonCallExpression,
  type PythonKeywordArgument,
} from "./skriptoteketPythonAnalysis";
import {
  SKRIPTOTEKET_CONTRACT_KEYS,
  SKRIPTOTEKET_NOTICE_LEVELS,
  SKRIPTOTEKET_OUTPUT_KINDS,
} from "./skriptoteketMetadata";
import {
  extractPythonArrayElements,
  extractPythonDictionaryEntries,
  findPythonFunctionDefinitions,
  findPythonImportModules,
  findPythonMemberCalls,
  findPythonRaiseStatements,
  findPythonReturnStatements,
  parsePythonStringLiteralValue,
  type PythonFunctionDefinition,
  type PythonNodeRange,
} from "./skriptoteketPythonTree";

const ST_BESTPRACTICE_TOOLUSERERROR_IMPORT = "ST_BESTPRACTICE_TOOLUSERERROR_IMPORT";
const ST_BESTPRACTICE_ENCODING = "ST_BESTPRACTICE_ENCODING";
const ST_BESTPRACTICE_WEASYPRINT_DIRECT = "ST_BESTPRACTICE_WEASYPRINT_DIRECT";
const ST_BESTPRACTICE_MKDIR = "ST_BESTPRACTICE_MKDIR";

const MSG_TOOLUSERERROR_IMPORT =
  "ToolUserError används men import saknas: `from tool_errors import ToolUserError`";
const MSG_ENCODING = "Ange `encoding=\"utf-8\"` vid textläsning/skrivning.";
const MSG_WEASYPRINT_DIRECT = "Använd `pdf_helper.save_as_pdf` istället för `weasyprint.HTML` direkt.";
const MSG_MKDIR = "Skapa gärna kataloger innan du skriver filer (särskilt undermappar).";

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

  function bestPracticeDiagnostics(state: EditorState, match: PythonFunctionDefinition | null): Diagnostic[] {
    if (!match || match.bodyFrom === null || match.bodyTo === null) return [];

    const range = { from: match.bodyFrom, to: match.bodyTo };
    const diagnostics: Diagnostic[] = [];

    const imports = buildPythonImportBindingsSnapshot(state);
    const calls = findPythonCallExpressions(state, range);
    const callsByRange = new Map(calls.map((call) => [`${call.from}:${call.to}`, call]));

    const toolErrorsModuleNames = new Set(
      [...imports.moduleBindings.entries()]
        .filter(([, modulePath]) => modulePath === "tool_errors")
        .map(([name]) => name),
    );
    const toolUserErrorNames = new Set(
      [...imports.fromBindings.entries()]
        .filter(([, entry]) => entry.modulePath === "tool_errors" && entry.importedName === "ToolUserError")
        .map(([name]) => name),
    );

    const raises = findPythonRaiseStatements(state, range);
    for (const raiseStatement of raises) {
      const raised = raiseStatement.expression;
      if (!raised || raised.name !== "CallExpression") continue;

      const call = callsByRange.get(`${raised.from}:${raised.to}`) ?? null;
      if (!call) continue;

      if (call.callee.kind === "variable" && call.callee.name === "ToolUserError") {
        if (!toolUserErrorNames.has("ToolUserError")) {
          diagnostics.push({
            from: call.callee.nameFrom,
            to: call.callee.nameTo,
            severity: "error",
            source: ST_BESTPRACTICE_TOOLUSERERROR_IMPORT,
            message: MSG_TOOLUSERERROR_IMPORT,
          });
        }
        continue;
      }

      if (call.callee.kind === "member" && call.callee.propertyName === "ToolUserError") {
        if (!toolErrorsModuleNames.has(call.callee.objectName)) {
          diagnostics.push({
            from: call.callee.propertyFrom,
            to: call.callee.propertyTo,
            severity: "error",
            source: ST_BESTPRACTICE_TOOLUSERERROR_IMPORT,
            message: MSG_TOOLUSERERROR_IMPORT,
          });
        }
      }
    }

    function findKeyword(call: PythonCallExpression, keyword: string): PythonKeywordArgument | null {
      return call.keywordArgs.find((arg) => arg.name === keyword) ?? null;
    }

    function parseStringLiteral(state: EditorState, node: PythonNodeRange | null): string | null {
      if (!node || node.name !== "String") return null;
      return parsePythonStringLiteralValue(state.doc.sliceString(node.from, node.to));
    }

    function openMode(call: PythonCallExpression): string {
      const keywordMode = findKeyword(call, "mode");
      const keywordModeValue = parseStringLiteral(state, keywordMode?.value ?? null);
      if (keywordModeValue) return keywordModeValue;

      const modeNode = call.positionalArgs[1] ?? null;
      const modeValue = parseStringLiteral(state, modeNode);
      return modeValue ?? "r";
    }

    function shouldSkipEncodingForOpenCall(call: PythonCallExpression): boolean {
      const mode = openMode(call);
      return mode.includes("b");
    }

    function hasEncodingKeyword(call: PythonCallExpression): boolean {
      return call.keywordArgs.some((arg) => arg.name === "encoding");
    }

    for (const call of calls) {
      if (call.callee.kind === "variable" && call.callee.name === "open") {
        if (shouldSkipEncodingForOpenCall(call)) continue;
        if (hasEncodingKeyword(call)) continue;
        diagnostics.push({
          from: call.callee.nameFrom,
          to: call.callee.nameTo,
          severity: "info",
          source: ST_BESTPRACTICE_ENCODING,
          message: MSG_ENCODING,
        });
        continue;
      }

      if (call.callee.kind !== "member") continue;

      if (call.callee.propertyName === "read_text") {
        if (hasEncodingKeyword(call)) continue;
        const encodingPositional = parseStringLiteral(state, call.positionalArgs[0] ?? null);
        if (encodingPositional) continue;

        diagnostics.push({
          from: call.callee.propertyFrom,
          to: call.callee.propertyTo,
          severity: "info",
          source: ST_BESTPRACTICE_ENCODING,
          message: MSG_ENCODING,
        });
        continue;
      }

      if (call.callee.propertyName === "write_text") {
        if (hasEncodingKeyword(call)) continue;
        const encodingPositional = parseStringLiteral(state, call.positionalArgs[1] ?? null);
        if (encodingPositional) continue;

        diagnostics.push({
          from: call.callee.propertyFrom,
          to: call.callee.propertyTo,
          severity: "info",
          source: ST_BESTPRACTICE_ENCODING,
          message: MSG_ENCODING,
        });
      }
    }

    const weasyprintModuleNames = new Set(
      [...imports.moduleBindings.entries()]
        .filter(([, modulePath]) => modulePath === "weasyprint")
        .map(([name]) => name),
    );
    const weasyprintHtmlNames = new Set(
      [...imports.fromBindings.entries()]
        .filter(([, entry]) => entry.modulePath === "weasyprint" && entry.importedName === "HTML")
        .map(([name]) => name),
    );

    for (const call of calls) {
      if (call.callee.kind === "variable" && weasyprintHtmlNames.has(call.callee.name)) {
        diagnostics.push({
          from: call.callee.nameFrom,
          to: call.callee.nameTo,
          severity: "info",
          source: ST_BESTPRACTICE_WEASYPRINT_DIRECT,
          message: MSG_WEASYPRINT_DIRECT,
        });
        continue;
      }

      if (
        call.callee.kind === "member" &&
        call.callee.propertyName === "HTML" &&
        weasyprintModuleNames.has(call.callee.objectName)
      ) {
        diagnostics.push({
          from: call.callee.propertyFrom,
          to: call.callee.propertyTo,
          severity: "info",
          source: ST_BESTPRACTICE_WEASYPRINT_DIRECT,
          message: MSG_WEASYPRINT_DIRECT,
        });
      }
    }

    function extractOutputDirSegment(source: string, opts: { requireNested: boolean }): string | null {
      const pattern = opts.requireNested
        ? /\boutput_dir\s*\/\s*(["'])([^"']+)\1\s*\//
        : /\boutput_dir\s*\/\s*(["'])([^"']+)\1/;
      const match = source.match(pattern);
      return match ? match[2] ?? null : null;
    }

    const mkdirBeforeFromBySegment = new Map<string, number>();
    for (const call of calls) {
      if (call.callee.kind !== "member" || call.callee.propertyName !== "mkdir") continue;
      const calleeText = state.doc.sliceString(call.callee.from, call.callee.to);
      const segment = extractOutputDirSegment(calleeText, { requireNested: false });
      if (!segment) continue;

      const existing = mkdirBeforeFromBySegment.get(segment);
      if (existing === undefined || call.from < existing) {
        mkdirBeforeFromBySegment.set(segment, call.from);
      }
    }

    const mkdirReportedSegments = new Set<string>();

    function ensureMkdirHint(call: PythonCallExpression, segment: string, from: number, to: number): void {
      const mkdirFrom = mkdirBeforeFromBySegment.get(segment);
      if (mkdirFrom !== undefined && mkdirFrom < call.from) return;
      if (mkdirReportedSegments.has(segment)) return;
      mkdirReportedSegments.add(segment);

      diagnostics.push({
        from,
        to,
        severity: "info",
        source: ST_BESTPRACTICE_MKDIR,
        message: MSG_MKDIR,
      });
    }

    function openModeIsWriting(mode: string): boolean {
      return /[wax+]/.test(mode);
    }

    for (const call of calls) {
      if (
        call.callee.kind === "member" &&
        (call.callee.propertyName === "write_text" || call.callee.propertyName === "write_bytes")
      ) {
        const calleeText = state.doc.sliceString(call.callee.from, call.callee.to);
        const segment = extractOutputDirSegment(calleeText, { requireNested: true });
        if (!segment) continue;
        ensureMkdirHint(call, segment, call.callee.propertyFrom, call.callee.propertyTo);
        continue;
      }

      if (call.callee.kind === "variable" && call.callee.name === "open") {
        const mode = openMode(call);
        if (!openModeIsWriting(mode)) continue;

        const callText = state.doc.sliceString(call.from, call.to);
        const segment = extractOutputDirSegment(callText, { requireNested: true });
        if (!segment) continue;
        ensureMkdirHint(call, segment, call.callee.nameFrom, call.callee.nameTo);
      }
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
        ...bestPracticeDiagnostics(view.state, match),
        ...securityDiagnostics(view.state),
      ];
    }),
  ];
}
