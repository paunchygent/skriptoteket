import type { EditorState } from "@codemirror/state";
import { syntaxTree } from "@codemirror/language";

export type PythonFunctionDefinition = {
  name: string;
  nameFrom: number;
  nameTo: number;
  params: string[];
  paramListFrom: number | null;
  paramListTo: number | null;
  bodyFrom: number | null;
  bodyTo: number | null;
};

export function findPythonFunctionDefinitions(state: EditorState): PythonFunctionDefinition[] {
  const tree = syntaxTree(state);
  const cursor = tree.cursor();
  const result: PythonFunctionDefinition[] = [];

  function parseParamList(): { params: string[]; from: number; to: number } {
    const params: string[] = [];
    const paramListFrom = cursor.from;
    const paramListTo = cursor.to;

    if (!cursor.firstChild()) {
      return { params, from: paramListFrom, to: paramListTo };
    }

    do {
      if (cursor.name === "VariableName") {
        params.push(state.doc.sliceString(cursor.from, cursor.to));
      }
    } while (cursor.nextSibling());

    cursor.parent();

    return { params, from: paramListFrom, to: paramListTo };
  }

  function parseFunctionDefinition(): PythonFunctionDefinition | null {
    const fnFrom = cursor.from;

    let name = "";
    let nameFrom = fnFrom;
    let nameTo = fnFrom;
    let params: string[] = [];
    let paramListFrom: number | null = null;
    let paramListTo: number | null = null;
    let bodyFrom: number | null = null;
    let bodyTo: number | null = null;

    if (!cursor.firstChild()) return null;
    do {
      if (cursor.name === "VariableName" && name === "") {
        name = state.doc.sliceString(cursor.from, cursor.to);
        nameFrom = cursor.from;
        nameTo = cursor.to;
      } else if (cursor.name === "ParamList") {
        const parsed = parseParamList();
        params = parsed.params;
        paramListFrom = parsed.from;
        paramListTo = parsed.to;
      } else if (cursor.name === "Body") {
        bodyFrom = cursor.from;
        bodyTo = cursor.to;
      }
    } while (cursor.nextSibling());
    cursor.parent();

    if (!name) return null;
    return { name, nameFrom, nameTo, params, paramListFrom, paramListTo, bodyFrom, bodyTo };
  }

  function walk(): void {
    do {
      if (cursor.name === "FunctionDefinition") {
        const parsed = parseFunctionDefinition();
        if (parsed) result.push(parsed);
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
