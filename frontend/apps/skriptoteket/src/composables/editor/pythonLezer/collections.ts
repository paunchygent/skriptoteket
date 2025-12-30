import type { EditorState } from "@codemirror/state";
import { syntaxTree } from "@codemirror/language";

import { parsePythonStringLiteralValue } from "./stringLiterals";
import type { PythonNodeRange } from "./types";

type TreeCursorLike = {
  name: string;
  from: number;
  to: number;
  firstChild: () => boolean;
  nextSibling: () => boolean;
  parent: () => boolean;
  moveTo: (pos: number, side?: -1 | 0 | 1) => boolean;
};

function cursorAtRange(cursor: TreeCursorLike, name: string, from: number, to: number): boolean {
  return cursor.name === name && cursor.from === from && cursor.to === to;
}

export type PythonDictEntry = {
  key: string;
  keyFrom: number;
  keyTo: number;
  value: PythonNodeRange | null;
};

export function extractPythonDictionaryEntries(
  state: EditorState,
  dict: { from: number; to: number },
): PythonDictEntry[] {
  const tree = syntaxTree(state);
  const cursor = tree.cursor() as unknown as TreeCursorLike;

  cursor.moveTo(dict.from, 1);
  while (!cursorAtRange(cursor, "DictionaryExpression", dict.from, dict.to)) {
    if (!cursor.parent()) return [];
  }

  const result: PythonDictEntry[] = [];
  let pendingKey: { key: string; from: number; to: number } | null = null;
  let expectingValue = false;

  if (!cursor.firstChild()) return result;

  do {
    if (!expectingValue && cursor.name === "String") {
      const raw = state.doc.sliceString(cursor.from, cursor.to);
      const key = parsePythonStringLiteralValue(raw);
      pendingKey = key ? { key, from: cursor.from, to: cursor.to } : null;
      continue;
    }

    if (cursor.name === ":" && pendingKey) {
      expectingValue = true;
      continue;
    }

    if (expectingValue && pendingKey) {
      result.push({
        key: pendingKey.key,
        keyFrom: pendingKey.from,
        keyTo: pendingKey.to,
        value: { name: cursor.name, from: cursor.from, to: cursor.to },
      });
      pendingKey = null;
      expectingValue = false;
    }
  } while (cursor.nextSibling());

  cursor.parent();
  return result;
}

export function extractPythonArrayElements(
  state: EditorState,
  array: { from: number; to: number },
): PythonNodeRange[] {
  const tree = syntaxTree(state);
  const cursor = tree.cursor() as unknown as TreeCursorLike;

  cursor.moveTo(array.from, 1);
  while (!cursorAtRange(cursor, "ArrayExpression", array.from, array.to)) {
    if (!cursor.parent()) return [];
  }

  const result: PythonNodeRange[] = [];

  if (!cursor.firstChild()) return result;
  do {
    if (cursor.name === "[" || cursor.name === "]" || cursor.name === ",") continue;
    result.push({ name: cursor.name, from: cursor.from, to: cursor.to });
  } while (cursor.nextSibling());
  cursor.parent();

  return result;
}
