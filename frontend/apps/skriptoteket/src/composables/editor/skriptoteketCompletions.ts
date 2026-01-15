import { closeCompletion, startCompletion, type Completion, type CompletionContext } from "@codemirror/autocomplete";
import { ensureSyntaxTree, syntaxTree } from "@codemirror/language";
import { pythonLanguage } from "@codemirror/lang-python";
import type { EditorState, Extension } from "@codemirror/state";
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
} from "./pythonLezer";

const MODULE_IDS = Array.from(new Set(SKRIPTOTEKET_HELPER_DOCS.map((doc) => doc.moduleId)));
const MODULE_ID_SET: ReadonlySet<string> = new Set(MODULE_IDS);

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
      type: /^[A-Z]/.test(entry.exportId) ? "class" : "function",
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

  // 2) `from <known_helper_module> import <name>`
  const helperExportMatch = prefix.match(/^\s*from\s+([a-zA-Z0-9_]+)\s+import\s+([a-zA-Z0-9_]*)$/);
  if (helperExportMatch) {
    const moduleId = helperExportMatch[1] ?? "";
    if (!MODULE_ID_SET.has(moduleId)) return null;

    const partial = helperExportMatch[2] ?? "";
    const options = exportCompletions(moduleId, partial).sort(sortByLabel);
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
    if (
      (current.name === "DictionaryExpression" ||
        current.name === "SetExpression" ||
        current.name === "SetComprehensionExpression") &&
      current.parent?.name === "ReturnStatement"
    ) {
      return current;
    }
    current = current.parent;
  }
  return null;
}

type ContractCompletionContext = {
  stringNode: PythonStringNode;
  contentFrom: number;
  partial: string;
  dictNode: PythonStringNode;
  returnDict: PythonStringNode;
  keyForValue: string | null;
  isInOutputsArray: boolean;
  outputKind: string | null;
};

function resolveContractCompletionContext(state: EditorState, pos: number): ContractCompletionContext | null {
  const tree = ensureSyntaxTree(state, pos, 200) ?? syntaxTree(state);
  const node = tree.resolveInner(pos, -1) as unknown as PythonStringNode;
  let current: PythonStringNode | null = node;
  while (current && current.name !== "String") current = current.parent;
  if (!current) return null;

  const raw = state.doc.sliceString(current.from, current.to);
  const quote = raw[0];
  if (quote !== "'" && quote !== '"') return null;

  const contentFrom = current.from + 1;
  if (pos < contentFrom) return null;
  const partial = state.doc.sliceString(contentFrom, pos);

  const dictNode = (function findDict(): PythonStringNode | null {
    let cursor: PythonStringNode | null = current;
    while (
      cursor &&
      cursor.name !== "DictionaryExpression" &&
      cursor.name !== "SetExpression" &&
      cursor.name !== "SetComprehensionExpression"
    ) {
      cursor = cursor.parent;
    }
    return cursor;
  })();

  if (!dictNode) return null;

  const returnDict = findReturnDictionary(dictNode);
  if (!returnDict) return null;

  const dictEntries = extractPythonDictionaryEntries(state, { from: dictNode.from, to: dictNode.to });
  const keyForValue =
    dictEntries.find((entry) => entry.value?.from === current.from && entry.value?.to === current.to)?.key ?? null;

  const returnEntries = extractPythonDictionaryEntries(state, { from: returnDict.from, to: returnDict.to });
  const outputsValue = returnEntries.find((entry) => entry.key === "outputs")?.value ?? null;
  const outputsArray = outputsValue && outputsValue.name === "ArrayExpression" ? outputsValue : null;

  const isInOutputsArray = Boolean(outputsArray && dictNode.from >= outputsArray.from && dictNode.to <= outputsArray.to);

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

  return {
    stringNode: current,
    contentFrom,
    partial,
    dictNode,
    returnDict,
    keyForValue,
    isInOutputsArray,
    outputKind,
  };
}

function contractCompletions(context: CompletionContext) {
  const resolved = resolveContractCompletionContext(context.state, context.pos);
  if (!resolved) return null;

  const { contentFrom, partial, dictNode, returnDict, keyForValue, isInOutputsArray, outputKind } = resolved;

  if (dictNode.from === returnDict.from && dictNode.to === returnDict.to && keyForValue === null) {
    const options = SKRIPTOTEKET_CONTRACT_KEYS.filter((key) => key.startsWith(partial)).map((key) => ({
      label: key,
      type: "property",
      detail: "Contract v2",
      boost: 100,
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
      .map((key) => ({ label: key, type: "property", detail: "Contract v2", boost: 100 }));

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
      boost: 100,
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
      boost: 100,
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
  const autoTriggerCompletions = EditorView.updateListener.of((update) => {
    if (!update.docChanged) return;

    const selection = update.state.selection.main;
    if (!selection.empty) return;

    const head = selection.head;

    // Import completions: trigger after `from ` and `import ` prefixes in code context.
    if (!isInNonCodeContext(update.state, head - 1)) {
      if (head >= 5 && update.state.doc.sliceString(head - 5, head) === "from ") {
        closeCompletion(update.view);
        startCompletion(update.view);
        return;
      }

      if (head >= 7 && update.state.doc.sliceString(head - 7, head) === "import ") {
        const line = update.state.doc.lineAt(head);
        const prefix = line.text.slice(0, head - line.from);
        const helperImportMatch = prefix.match(/^\s*from\s+([a-zA-Z0-9_]+)\s+import\s*$/);
        if (helperImportMatch && MODULE_ID_SET.has(helperImportMatch[1] ?? "")) {
          closeCompletion(update.view);
          startCompletion(update.view);
        }
      }
    }

    // Contract completions: auto-trigger on first typed character in the supported contexts.
    if (head <= 0) return;
    const lastChar = update.state.doc.sliceString(head - 1, head);
    if (!/^[a-zA-Z_]$/.test(lastChar)) return;

    const contractContext = resolveContractCompletionContext(update.state, head);
    if (!contractContext) return;
    if (contractContext.partial.length !== 1) return;

    const shouldTriggerTopLevelKeys =
      contractContext.dictNode.from === contractContext.returnDict.from &&
      contractContext.dictNode.to === contractContext.returnDict.to &&
      contractContext.keyForValue === null;

    const shouldTriggerOutputKeys = contractContext.isInOutputsArray && contractContext.keyForValue === null;

    const shouldTriggerOutputKindValues = contractContext.isInOutputsArray && contractContext.keyForValue === "kind";

    const shouldTriggerNoticeLevelValues =
      contractContext.isInOutputsArray &&
      contractContext.outputKind === "notice" &&
      contractContext.keyForValue === "level";

    if (
      shouldTriggerTopLevelKeys ||
      shouldTriggerOutputKeys ||
      shouldTriggerOutputKindValues ||
      shouldTriggerNoticeLevelValues
    ) {
      setTimeout(() => {
        closeCompletion(update.view);
        startCompletion(update.view);
      }, 0);
    }
  });

  return [
    pythonLanguage.data.of({
      autocomplete: (context: CompletionContext) =>
        skriptoteketImportCompletions(context) ?? contractCompletions(context),
    }),
    autoTriggerCompletions,
  ];
}
