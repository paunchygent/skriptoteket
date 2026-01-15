import type { DomainDiagnostic } from "../diagnostics";
import type { FixIntent } from "../fixIntents";
import type { LintRule } from "../lintRule";
import type { LinterContext } from "../linterContext";
import type { PythonCallExpression, PythonKeywordArgument, PythonNodeRange } from "../pythonFacts";
import { parsePythonStringLiteralValue } from "../utils/pythonStringLiterals";
import { findImportInsertPosition } from "../utils/pythonImports";

const ST_BESTPRACTICE_TOOLUSERERROR_IMPORT = "ST_BESTPRACTICE_TOOLUSERERROR_IMPORT";
const ST_BESTPRACTICE_TOOLKIT_IMPORT = "ST_BESTPRACTICE_TOOLKIT_IMPORT";
const ST_BESTPRACTICE_TOOLKIT_ENV = "ST_BESTPRACTICE_TOOLKIT_ENV";
const ST_BESTPRACTICE_ENCODING = "ST_BESTPRACTICE_ENCODING";
const ST_BESTPRACTICE_WEASYPRINT_DIRECT = "ST_BESTPRACTICE_WEASYPRINT_DIRECT";
const ST_BESTPRACTICE_MKDIR = "ST_BESTPRACTICE_MKDIR";

const MSG_TOOLUSERERROR_IMPORT =
  "ToolUserError används men import saknas: `from tool_errors import ToolUserError`";
const MSG_TOOLKIT_ENV = "Använd `skriptoteket_toolkit` istället för att läsa env-JSON direkt.";
const MSG_ENCODING = "Ange `encoding=\"utf-8\"` vid textläsning/skrivning.";
const MSG_WEASYPRINT_DIRECT = "Använd `pdf_helper.save_as_pdf` istället för `weasyprint.HTML` direkt.";
const MSG_MKDIR = "Skapa gärna kataloger innan du skriver filer (särskilt undermappar).";

const FIX_ADD_IMPORT = "Lägg till import";
const FIX_ADD_ENCODING = "Lägg till encoding";

function findKeyword(call: PythonCallExpression, keyword: string): PythonKeywordArgument | null {
  return call.keywordArgs.find((arg) => arg.name === keyword) ?? null;
}

function parseStringLiteral(text: string, node: PythonNodeRange | null): string | null {
  if (!node || node.name !== "String") return null;
  return parsePythonStringLiteralValue(text.slice(node.from, node.to));
}

function openMode(text: string, call: PythonCallExpression): string {
  const keywordMode = findKeyword(call, "mode");
  const keywordModeValue = parseStringLiteral(text, keywordMode?.value ?? null);
  if (keywordModeValue) return keywordModeValue;

  const modeNode = call.positionalArgs[1] ?? null;
  const modeValue = parseStringLiteral(text, modeNode);
  return modeValue ?? "r";
}

function shouldSkipEncodingForOpenCall(text: string, call: PythonCallExpression): boolean {
  const mode = openMode(text, call);
  return mode.includes("b");
}

function hasEncodingKeyword(call: PythonCallExpression): boolean {
  return call.keywordArgs.some((arg) => arg.name === "encoding");
}

function openModeIsWriting(mode: string): boolean {
  return /[wax+]/.test(mode);
}

function addEncodingFix(ctxText: string, call: PythonCallExpression): FixIntent | null {
  let argListFrom = call.argListFrom;
  let argListTo = call.argListTo;

  if (argListFrom === null || argListTo === null) {
    const closeParenPos = call.to - 1;
    if ((ctxText[closeParenPos] ?? "") !== ")") return null;

    let depth = 0;
    for (let pos = closeParenPos; pos >= call.from; pos -= 1) {
      const ch = ctxText[pos] ?? "";
      if (ch === ")") {
        depth += 1;
        continue;
      }
      if (ch === "(") {
        depth -= 1;
        if (depth === 0) {
          argListFrom = pos;
          argListTo = closeParenPos + 1;
          break;
        }
      }
    }
  }

  if (argListFrom === null || argListTo === null) return null;

  const openParenPos = argListFrom;
  const closeParenPos = argListTo - 1;

  const positionalEnds = call.positionalArgs.map((arg) => arg.to);
  const keywordEnds = call.keywordArgs.map((arg) => arg.value?.to ?? arg.nameTo);
  const lastArgEnd = Math.max(...positionalEnds, ...keywordEnds, openParenPos);
  const hasArgs = lastArgEnd !== openParenPos;

  let insertAt = openParenPos + 1;
  let prefix = "";

  if (hasArgs) {
    let scan = lastArgEnd;
    while (scan < closeParenPos && /\s/.test(ctxText[scan] ?? "")) scan += 1;

    if ((ctxText[scan] ?? "") === ",") {
      insertAt = scan + 1;
      prefix = " ";
    } else {
      insertAt = lastArgEnd;
      prefix = ", ";
    }
  }

  const text = `${prefix}encoding="utf-8"`;

  return { kind: "insertText", label: FIX_ADD_ENCODING, at: insertAt, text };
}

export const BestPracticesRule: LintRule = {
  id: "ST_BEST_PRACTICES",
  check(ctx: LinterContext): DomainDiagnostic[] {
    const match = ctx.facts.entrypoint;
    if (!match) return [];

    const diagnostics: DomainDiagnostic[] = [];

    const imports = ctx.facts.imports;
    const calls = ctx.facts.calls;
    const callsByRange = new Map(calls.map((call) => [`${call.from}:${call.to}`, call]));

    const toolUserErrorImportAt = findImportInsertPosition(ctx.text);
    const toolUserErrorImportPrefix =
      toolUserErrorImportAt > 0 && ctx.text[toolUserErrorImportAt - 1] !== "\n" ? "\n" : "";
    const toolUserErrorFromImportFix: FixIntent = {
      kind: "insertText",
      label: FIX_ADD_IMPORT,
      at: toolUserErrorImportAt,
      text: `${toolUserErrorImportPrefix}from tool_errors import ToolUserError\n`,
    };

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

    for (const raiseStatement of ctx.facts.raises) {
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
            fixes: [toolUserErrorFromImportFix],
          });
        }
        continue;
      }

      if (call.callee.kind === "member" && call.callee.propertyName === "ToolUserError") {
        if (!toolErrorsModuleNames.has(call.callee.objectName)) {
          const toolUserErrorModuleImport = call.callee.objectName === "tool_errors"
            ? "import tool_errors\n"
            : `import tool_errors as ${call.callee.objectName}\n`;
          const toolUserErrorModuleFix: FixIntent = {
            kind: "insertText",
            label: FIX_ADD_IMPORT,
            at: toolUserErrorImportAt,
            text: `${toolUserErrorImportPrefix}${toolUserErrorModuleImport}`,
          };
          diagnostics.push({
            from: call.callee.propertyFrom,
            to: call.callee.propertyTo,
            severity: "error",
            source: ST_BESTPRACTICE_TOOLUSERERROR_IMPORT,
            message: MSG_TOOLUSERERROR_IMPORT,
            fixes: [toolUserErrorModuleFix],
          });
        }
      }
    }

    const toolkitModuleNames = new Set(
      [...imports.moduleBindings.entries()]
        .filter(([, modulePath]) => modulePath === "skriptoteket_toolkit")
        .map(([name]) => name),
    );

    const toolkitFromNames = new Set(
      [...imports.fromBindings.entries()]
        .filter(([, entry]) => entry.modulePath === "skriptoteket_toolkit")
        .map(([name]) => name),
    );

    const toolkitExports = new Set([
      "read_inputs",
      "read_input_manifest",
      "list_input_files",
      "read_action",
      "get_action_parts",
      "read_memory",
      "read_settings",
    ]);

    const localFunctionNames = new Set(ctx.facts.functions.map((fn) => fn.name));

    const missingToolkitNames = new Map<string, { from: number; to: number }>();
    for (const call of calls) {
      if (call.callee.kind !== "variable") continue;
      if (!toolkitExports.has(call.callee.name)) continue;
      if (localFunctionNames.has(call.callee.name)) continue;
      if (toolkitFromNames.has(call.callee.name)) continue;

      const existing = missingToolkitNames.get(call.callee.name);
      if (!existing || call.callee.nameFrom < existing.from) {
        missingToolkitNames.set(call.callee.name, { from: call.callee.nameFrom, to: call.callee.nameTo });
      }
    }

    if (missingToolkitNames.size > 0) {
      const toolkitImportAt = findImportInsertPosition(ctx.text);
      const toolkitImportPrefix =
        toolkitImportAt > 0 && ctx.text[toolkitImportAt - 1] !== "\n" ? "\n" : "";

      const missing = [...missingToolkitNames.keys()].sort();
      const importLine = `from skriptoteket_toolkit import ${missing.join(", ")}\n`;
      const toolkitFix: FixIntent = {
        kind: "insertText",
        label: FIX_ADD_IMPORT,
        at: toolkitImportAt,
        text: `${toolkitImportPrefix}${importLine}`,
      };

      const first = [...missingToolkitNames.values()].sort((a, b) => a.from - b.from)[0] ?? null;
      if (first) {
        diagnostics.push({
          from: first.from,
          to: first.to,
          severity: "error",
          source: ST_BESTPRACTICE_TOOLKIT_IMPORT,
          message: `Skriptoteket toolkit används men import saknas: \`${importLine.trimEnd()}\``,
          fixes: [toolkitFix],
        });
      }
    }

    if (!toolkitModuleNames.has("skriptoteket_toolkit")) {
      const firstModuleCall = calls.find(
        (call) =>
          call.callee.kind === "member" &&
          call.callee.objectName === "skriptoteket_toolkit" &&
          toolkitExports.has(call.callee.propertyName),
      );

      if (firstModuleCall?.callee.kind === "member") {
        const toolkitModuleImportAt = findImportInsertPosition(ctx.text);
        const toolkitModuleImportPrefix =
          toolkitModuleImportAt > 0 && ctx.text[toolkitModuleImportAt - 1] !== "\n" ? "\n" : "";

        const importLine = "import skriptoteket_toolkit\n";
        const toolkitModuleFix: FixIntent = {
          kind: "insertText",
          label: FIX_ADD_IMPORT,
          at: toolkitModuleImportAt,
          text: `${toolkitModuleImportPrefix}${importLine}`,
        };

        diagnostics.push({
          from: firstModuleCall.callee.propertyFrom,
          to: firstModuleCall.callee.propertyTo,
          severity: "error",
          source: ST_BESTPRACTICE_TOOLKIT_IMPORT,
          message: `Skriptoteket toolkit används men import saknas: \`${importLine.trimEnd()}\``,
          fixes: [toolkitModuleFix],
        });
      }
    }

    function toolkitSuggestionForEnvVar(envVar: string): string | null {
      if (envVar === "SKRIPTOTEKET_INPUTS") return "Använd `read_inputs()` från `skriptoteket_toolkit`.";
      if (envVar === "SKRIPTOTEKET_INPUT_MANIFEST") {
        return "Använd `list_input_files()` (eller `read_input_manifest()`) från `skriptoteket_toolkit`.";
      }
      if (envVar === "SKRIPTOTEKET_ACTION") {
        return "Använd `get_action_parts()` (eller `read_action()`) från `skriptoteket_toolkit`.";
      }
      if (envVar === "SKRIPTOTEKET_MEMORY_PATH") {
        return "Använd `read_settings()` (eller `read_memory()`) från `skriptoteket_toolkit`.";
      }
      if (envVar === "SKRIPTOTEKET_INPUT_DIR") return "Använd `input_dir`-parametern i `run_tool`.";
      if (envVar === "SKRIPTOTEKET_OUTPUT_DIR") return "Använd `output_dir`-parametern i `run_tool`.";
      return null;
    }

    const envAccessPattern =
      /\bos\s*\.\s*(?:environ\s*\.\s*get|getenv)\s*\(\s*(['"])(SKRIPTOTEKET_[A-Z0-9_]+)\1/g;
    const reportedEnvVars = new Set<string>();

    for (const call of calls) {
      const callText = ctx.text.slice(call.from, call.to);
      for (const match of callText.matchAll(envAccessPattern)) {
        const envVar = match[2] ?? "";
        if (!envVar || reportedEnvVars.has(envVar)) continue;
        const suggestion = toolkitSuggestionForEnvVar(envVar);
        if (!suggestion) continue;

        reportedEnvVars.add(envVar);

        const matchIndex = match.index ?? 0;
        const envVarFrom = matchIndex + match[0].indexOf(envVar);
        const from = call.from + envVarFrom;
        const to = from + envVar.length;

        diagnostics.push({
          from,
          to,
          severity: "info",
          source: ST_BESTPRACTICE_TOOLKIT_ENV,
          message: `${MSG_TOOLKIT_ENV} ${suggestion}`,
        });
      }
    }

    for (const call of calls) {
      if (call.callee.kind === "variable" && call.callee.name === "open") {
        if (shouldSkipEncodingForOpenCall(ctx.text, call)) continue;
        if (hasEncodingKeyword(call)) continue;
        const fix = addEncodingFix(ctx.text, call);
        diagnostics.push({
          from: call.callee.nameFrom,
          to: call.callee.nameTo,
          severity: "info",
          source: ST_BESTPRACTICE_ENCODING,
          message: MSG_ENCODING,
          fixes: fix ? [fix] : undefined,
        });
        continue;
      }

      if (call.callee.kind !== "member") continue;

      if (call.callee.propertyName === "read_text") {
        if (hasEncodingKeyword(call)) continue;
        const encodingPositional = parseStringLiteral(ctx.text, call.positionalArgs[0] ?? null);
        if (encodingPositional) continue;

        const fix = addEncodingFix(ctx.text, call);
        diagnostics.push({
          from: call.callee.propertyFrom,
          to: call.callee.propertyTo,
          severity: "info",
          source: ST_BESTPRACTICE_ENCODING,
          message: MSG_ENCODING,
          fixes: fix ? [fix] : undefined,
        });
        continue;
      }

      if (call.callee.propertyName === "write_text") {
        if (hasEncodingKeyword(call)) continue;
        const encodingPositional = parseStringLiteral(ctx.text, call.positionalArgs[1] ?? null);
        if (encodingPositional) continue;

        const fix = addEncodingFix(ctx.text, call);
        diagnostics.push({
          from: call.callee.propertyFrom,
          to: call.callee.propertyTo,
          severity: "info",
          source: ST_BESTPRACTICE_ENCODING,
          message: MSG_ENCODING,
          fixes: fix ? [fix] : undefined,
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
      const calleeText = ctx.text.slice(call.callee.from, call.callee.to);
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

    for (const call of calls) {
      if (
        call.callee.kind === "member" &&
        (call.callee.propertyName === "write_text" || call.callee.propertyName === "write_bytes")
      ) {
        const calleeText = ctx.text.slice(call.callee.from, call.callee.to);
        const segment = extractOutputDirSegment(calleeText, { requireNested: true });
        if (!segment) continue;
        ensureMkdirHint(call, segment, call.callee.propertyFrom, call.callee.propertyTo);
        continue;
      }

      if (call.callee.kind === "variable" && call.callee.name === "open") {
        const mode = openMode(ctx.text, call);
        if (!openModeIsWriting(mode)) continue;

        const callText = ctx.text.slice(call.from, call.to);
        const segment = extractOutputDirSegment(callText, { requireNested: true });
        if (!segment) continue;
        ensureMkdirHint(call, segment, call.callee.nameFrom, call.callee.nameTo);
      }
    }

    return diagnostics;
  },
};
