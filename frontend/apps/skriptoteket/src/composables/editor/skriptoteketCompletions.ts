import { closeCompletion, startCompletion, type Completion, type CompletionContext } from "@codemirror/autocomplete";
import { syntaxTree } from "@codemirror/language";
import { pythonLanguage } from "@codemirror/lang-python";
import type { Extension } from "@codemirror/state";
import { EditorView } from "@codemirror/view";

import type { SkriptoteketIntelligenceConfig } from "./skriptoteketIntelligence";
import {
  SKRIPTOTEKET_CONTRACT_KEYS,
  SKRIPTOTEKET_HELPER_DOCS,
  SKRIPTOTEKET_NOTICE_LEVELS,
  SKRIPTOTEKET_OUTPUT_KINDS,
} from "./skriptoteketMetadata";
import {
  extractPythonDictionaryEntries,
  isInNonCodeContext,
  parsePythonStringLiteralValue,
} from "./skriptoteketPythonTree";

const MODULE_IDS = Array.from(new Set(SKRIPTOTEKET_HELPER_DOCS.map((doc) => doc.moduleId)));

const EXPORTS_BY_MODULE = SKRIPTOTEKET_HELPER_DOCS.reduce(
  (acc, doc) => {
    const list = acc.get(doc.moduleId) ?? [];
    list.push(doc);
    acc.set(doc.moduleId, list);
    return acc;
  },
  new Map<string, typeof SKRIPTOTEKET_HELPER_DOCS>(),
);

function sortByLabel(a: Completion, b: Completion): number {
  return a.label.localeCompare(b.label);
}

function moduleCompletions(partial: string): Completion[] {
  return MODULE_IDS.filter((moduleId) => moduleId.startsWith(partial)).map((moduleId) => ({
    label: moduleId,
    type: "module",
    detail: "Skriptoteket",
    boost: 100,
  }));
}

function exportCompletions(moduleId: string, partial: string): Completion[] {
  const entries = EXPORTS_BY_MODULE.get(moduleId) ?? [];
  return entries
    .filter((entry) => entry.exportId.startsWith(partial))
    .map((entry) => ({
      label: entry.exportId,
      type: entry.exportId === "ToolUserError" ? "class" : "function",
      detail: entry.signature,
      info: entry.swedishDoc,
      boost: 100,
    }));
}

function skriptoteketImportCompletions(context: CompletionContext) {
  const { state, pos } = context;
  if (isInNonCodeContext(state, pos)) return null;

  const line = state.doc.lineAt(pos);
  const prefix = line.text.slice(0, pos - line.from);

  // 1) `from <module>`
  const moduleMatch = prefix.match(/^\s*from\s*([a-zA-Z0-9_]*)$/);
  if (moduleMatch) {
    const partial = moduleMatch[1] ?? "";
    const options = moduleCompletions(partial).sort(sortByLabel);
    if (options.length === 0) return null;
    return {
      from: pos - partial.length,
      options,
      validFor: /^[a-zA-Z0-9_]*$/,
    };
  }

  // 2) `from pdf_helper import <name>`
  const pdfMatch = prefix.match(/^\s*from\s+pdf_helper\s+import\s+([a-zA-Z0-9_]*)$/);
  if (pdfMatch) {
    const partial = pdfMatch[1] ?? "";
    const options = exportCompletions("pdf_helper", partial).sort(sortByLabel);
    if (options.length === 0) return null;
    return {
      from: pos - partial.length,
      options,
      validFor: /^[a-zA-Z0-9_]*$/,
    };
  }

  // 3) `from tool_errors import <name>`
  const toolErrorsMatch = prefix.match(/^\s*from\s+tool_errors\s+import\s+([a-zA-Z0-9_]*)$/);
  if (toolErrorsMatch) {
    const partial = toolErrorsMatch[1] ?? "";
    const options = exportCompletions("tool_errors", partial).sort(sortByLabel);
    if (options.length === 0) return null;
    return {
      from: pos - partial.length,
      options,
      validFor: /^[a-zA-Z0-9_]*$/,
    };
  }

  return null;
}

type PythonStringNode = { name: string; from: number; to: number; parent: PythonStringNode | null };

function findReturnDictionary(node: PythonStringNode | null): PythonStringNode | null {
  let current: PythonStringNode | null = node;
  while (current) {
    if (current.name === "DictionaryExpression" && current.parent?.name === "ReturnStatement") {
      return current;
    }
    current = current.parent;
  }
  return null;
}

function resolveStringNode(
  context: CompletionContext,
): { node: PythonStringNode; contentFrom: number; partial: string } | null {
  const { state, pos } = context;
  const node = syntaxTree(state).resolveInner(pos, -1) as unknown as PythonStringNode;
  let current: PythonStringNode | null = node;
  while (current && current.name !== "String") current = current.parent;
  if (!current || current.name !== "String") return null;

  const raw = state.doc.sliceString(current.from, current.to);
  const quote = raw[0];
  if (quote !== "'" && quote !== '"') return null;

  const contentFrom = current.from + 1;
  if (pos < contentFrom) return null;
  const partial = state.doc.sliceString(contentFrom, pos);
  return { node: current, contentFrom, partial };
}

function contractCompletions(context: CompletionContext) {
  const { state } = context;
  const resolved = resolveStringNode(context);
  if (!resolved) return null;

  const { node: stringNode, contentFrom, partial } = resolved;
  const dictNode = (function findDict(): PythonStringNode | null {
    let current: PythonStringNode | null = stringNode;
    while (current && current.name !== "DictionaryExpression") current = current.parent;
    return current;
  })();

  if (!dictNode) return null;

  const returnDict = findReturnDictionary(dictNode);
  if (!returnDict) return null;

  const dictEntries = extractPythonDictionaryEntries(state, { from: dictNode.from, to: dictNode.to });
  const keyForValue =
    dictEntries.find((entry) => entry.value?.from === stringNode.from && entry.value?.to === stringNode.to)?.key ??
    null;

  const returnEntries = extractPythonDictionaryEntries(state, { from: returnDict.from, to: returnDict.to });
  const outputsValue =
    returnEntries.find((entry) => entry.key === "outputs")?.value ?? null;
  const outputsArray =
    outputsValue && outputsValue.name === "ArrayExpression" ? outputsValue : null;

  const isInOutputsArray =
    outputsArray && dictNode.from >= outputsArray.from && dictNode.to <= outputsArray.to;

  const outputKind =
    isInOutputsArray && dictNode.name === "DictionaryExpression"
      ? (() => {
          const fields = extractPythonDictionaryEntries(state, { from: dictNode.from, to: dictNode.to });
          const kindValue = fields.find((entry) => entry.key === "kind")?.value ?? null;
          if (!kindValue || kindValue.name !== "String") return null;
          const parsed = parsePythonStringLiteralValue(state.doc.sliceString(kindValue.from, kindValue.to));
          return parsed ?? null;
        })()
      : null;

  if (dictNode.from === returnDict.from && dictNode.to === returnDict.to && keyForValue === null) {
    const options = SKRIPTOTEKET_CONTRACT_KEYS.filter((key) => key.startsWith(partial)).map((key) => ({
      label: key,
      type: "property",
      detail: "Contract v2",
    }));

    if (options.length === 0) return null;
    return {
      from: contentFrom,
      options: options.sort(sortByLabel),
      validFor: /^[a-zA-Z0-9_]*$/,
    };
  }

  if (isInOutputsArray && keyForValue === null) {
    const keys = ["kind", ...(outputKind === "notice" ? ["level", "message"] : [])];
    const options = keys
      .filter((key) => key.startsWith(partial))
      .map((key) => ({ label: key, type: "property", detail: "Contract v2" }));

    if (options.length === 0) return null;
    return {
      from: contentFrom,
      options: options.sort(sortByLabel),
      validFor: /^[a-zA-Z0-9_]*$/,
    };
  }

  if (isInOutputsArray && keyForValue === "kind") {
    const options = SKRIPTOTEKET_OUTPUT_KINDS.filter((kind) => kind.startsWith(partial)).map((kind) => ({
      label: kind,
      type: "keyword",
      detail: "Contract v2",
    }));

    if (options.length === 0) return null;
    return {
      from: contentFrom,
      options: options.sort(sortByLabel),
      validFor: /^[a-zA-Z0-9_]*$/,
    };
  }

  if (isInOutputsArray && outputKind === "notice" && keyForValue === "level") {
    const options = SKRIPTOTEKET_NOTICE_LEVELS.filter((level) => level.startsWith(partial)).map((level) => ({
      label: level,
      type: "keyword",
      detail: "Contract v2",
    }));

    if (options.length === 0) return null;
    return {
      from: contentFrom,
      options: options.sort(sortByLabel),
      validFor: /^[a-zA-Z0-9_]*$/,
    };
  }

  return null;
}

export function skriptoteketCompletions(_config: SkriptoteketIntelligenceConfig): Extension {
  const autoTriggerFromImports = EditorView.updateListener.of((update) => {
    if (!update.docChanged) return;

    const selection = update.state.selection.main;
    if (!selection.empty) return;

    const head = selection.head;
    if (isInNonCodeContext(update.state, head - 1)) return;

    if (head >= 5 && update.state.doc.sliceString(head - 5, head) === "from ") {
      closeCompletion(update.view);
      startCompletion(update.view);
      return;
    }

    if (head >= 7 && update.state.doc.sliceString(head - 7, head) === "import ") {
      const line = update.state.doc.lineAt(head);
      const prefix = line.text.slice(0, head - line.from);
      if (/^\s*from\s+(pdf_helper|tool_errors)\s+import\s*$/.test(prefix)) {
        closeCompletion(update.view);
        startCompletion(update.view);
      }
    }
  });

  return [
    pythonLanguage.data.of({
      autocomplete: (context: CompletionContext) =>
        skriptoteketImportCompletions(context) ?? contractCompletions(context),
    }),
    autoTriggerFromImports,
  ];
}
