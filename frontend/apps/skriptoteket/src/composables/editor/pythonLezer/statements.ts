import type { EditorState } from "@codemirror/state";
import { syntaxTree } from "@codemirror/language";

import type { PythonNodeRange } from "./types";

export type PythonReturnStatement = {
  from: number;
  to: number;
  expression: PythonNodeRange | null;
};

export function findPythonReturnStatements(
  state: EditorState,
  range: { from: number; to: number },
): PythonReturnStatement[] {
  const tree = syntaxTree(state);
  const cursor = tree.cursor();
  const result: PythonReturnStatement[] = [];

  function parseReturnExpression(): PythonNodeRange | null {
    if (!cursor.firstChild()) return null;

    let expression: PythonNodeRange | null = null;
    do {
      if (cursor.name === "return") continue;
      expression = { name: cursor.name, from: cursor.from, to: cursor.to };
      break;
    } while (cursor.nextSibling());
    cursor.parent();
    return expression;
  }

  function walk(): void {
    do {
      if (cursor.to < range.from) continue;
      if (cursor.from > range.to) return;

      if (cursor.name === "ReturnStatement") {
        const expression = parseReturnExpression();
        result.push({ from: cursor.from, to: cursor.to, expression });
        continue;
      }

      if (cursor.firstChild()) {
        walk();
        cursor.parent();
      }
    } while (cursor.nextSibling());
  }

  walk();
  return result;
}

export type PythonRaiseStatement = {
  from: number;
  to: number;
  expression: PythonNodeRange | null;
};

export function findPythonRaiseStatements(
  state: EditorState,
  range: { from: number; to: number },
): PythonRaiseStatement[] {
  const tree = syntaxTree(state);
  const cursor = tree.cursor();
  const result: PythonRaiseStatement[] = [];

  function parseRaiseExpression(): PythonNodeRange | null {
    if (!cursor.firstChild()) return null;

    let expression: PythonNodeRange | null = null;
    do {
      if (cursor.name === "raise") continue;
      if (cursor.name === "from") break;
      expression = { name: cursor.name, from: cursor.from, to: cursor.to };
      break;
    } while (cursor.nextSibling());
    cursor.parent();
    return expression;
  }

  function walk(): void {
    do {
      if (cursor.to < range.from) continue;
      if (cursor.from > range.to) return;

      if (cursor.name === "RaiseStatement") {
        const expression = parseRaiseExpression();
        result.push({ from: cursor.from, to: cursor.to, expression });
        continue;
      }

      if (cursor.firstChild()) {
        walk();
        cursor.parent();
      }
    } while (cursor.nextSibling());
  }

  walk();
  return result;
}
