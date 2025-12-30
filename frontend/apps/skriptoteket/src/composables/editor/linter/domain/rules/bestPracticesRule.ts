import type { DomainDiagnostic } from "../diagnostics";
import type { LintRule } from "../lintRule";
import type { LinterContext } from "../linterContext";
import type { PythonCallExpression, PythonKeywordArgument, PythonNodeRange } from "../pythonFacts";
import { parsePythonStringLiteralValue } from "../utils/pythonStringLiterals";

const ST_BESTPRACTICE_TOOLUSERERROR_IMPORT = "ST_BESTPRACTICE_TOOLUSERERROR_IMPORT";
const ST_BESTPRACTICE_ENCODING = "ST_BESTPRACTICE_ENCODING";
const ST_BESTPRACTICE_WEASYPRINT_DIRECT = "ST_BESTPRACTICE_WEASYPRINT_DIRECT";
const ST_BESTPRACTICE_MKDIR = "ST_BESTPRACTICE_MKDIR";

const MSG_TOOLUSERERROR_IMPORT =
  "ToolUserError används men import saknas: `from tool_errors import ToolUserError`";
const MSG_ENCODING = "Ange `encoding=\"utf-8\"` vid textläsning/skrivning.";
const MSG_WEASYPRINT_DIRECT = "Använd `pdf_helper.save_as_pdf` istället för `weasyprint.HTML` direkt.";
const MSG_MKDIR = "Skapa gärna kataloger innan du skriver filer (särskilt undermappar).";

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

export const BestPracticesRule: LintRule = {
  id: "ST_BEST_PRACTICES",
  check(ctx: LinterContext): DomainDiagnostic[] {
    const match = ctx.facts.entrypoint;
    if (!match) return [];

    const diagnostics: DomainDiagnostic[] = [];

    const imports = ctx.facts.imports;
    const calls = ctx.facts.calls;
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

    for (const call of calls) {
      if (call.callee.kind === "variable" && call.callee.name === "open") {
        if (shouldSkipEncodingForOpenCall(ctx.text, call)) continue;
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
        const encodingPositional = parseStringLiteral(ctx.text, call.positionalArgs[0] ?? null);
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
        const encodingPositional = parseStringLiteral(ctx.text, call.positionalArgs[1] ?? null);
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
