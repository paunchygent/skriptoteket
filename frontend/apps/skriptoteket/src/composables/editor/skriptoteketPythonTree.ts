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

const NON_CODE_CONTEXTS = new Set(["String", "FormatString", "Comment"]);

export function isInNonCodeContext(state: EditorState, pos: number): boolean {
  type NamedNode = { name: string; parent: NamedNode | null };

  const resolvedPos = Math.max(0, Math.min(pos, state.doc.length));
  let node: NamedNode | null = syntaxTree(state).resolveInner(resolvedPos, -1) as unknown as NamedNode;
  while (node) {
    if (NON_CODE_CONTEXTS.has(node.name)) return true;
    node = node.parent;
  }
  return false;
}

export function resolvePythonIdentifierNode(
  state: EditorState,
  pos: number,
  side: -1 | 0 | 1,
): { from: number; to: number; name: string } | null {
  const resolvedPos = Math.max(0, Math.min(pos, state.doc.length));
  const node = syntaxTree(state).resolveInner(resolvedPos, side);
  if (node.name !== "VariableName" && node.name !== "PropertyName") return null;
  return {
    from: node.from,
    to: node.to,
    name: state.doc.sliceString(node.from, node.to),
  };
}

export function parsePythonStringLiteralValue(raw: string): string | null {
  if (raw.length < 2) return null;

  const quote = raw[0];
  if (quote !== "'" && quote !== '"') return null;
  if (raw[raw.length - 1] !== quote) return null;

  return raw.slice(1, -1);
}

export type PythonNodeRange = {
  name: string;
  from: number;
  to: number;
};

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

function cursorNameIs(cursor: TreeCursorLike, name: string): boolean {
  return cursor.name === name;
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

export type PythonImportModule = {
  from: number;
  to: number;
  modulePath: string;
};

export function findPythonImportModules(state: EditorState): PythonImportModule[] {
  const tree = syntaxTree(state);
  const cursor = tree.cursor();
  const result: PythonImportModule[] = [];

  function parseImportModulePaths(): string[] {
    const modules: string[] = [];

    if (!cursor.firstChild()) return modules;

    let mode: "none" | "from" | "import" = "none";
    let parts: string[] = [];
    let skippingAlias = false;

    do {
      if (cursor.name === "from") {
        mode = "from";
        continue;
      }

      if (cursor.name === "import") {
        if (mode === "from") break;
        mode = "import";
        continue;
      }

      if (mode === "none") continue;

      if (mode === "import" && cursor.name === ",") {
        if (parts.length > 0) modules.push(parts.join(""));
        parts = [];
        skippingAlias = false;
        continue;
      }

      if (cursor.name === "as") {
        skippingAlias = true;
        continue;
      }

      if (skippingAlias) continue;

      if (cursor.name === "VariableName") {
        parts.push(state.doc.sliceString(cursor.from, cursor.to));
      } else if (cursor.name === ".") {
        parts.push(".");
      }
    } while (cursor.nextSibling());

    cursor.parent();

    if (parts.length > 0) modules.push(parts.join(""));
    return modules;
  }

  function walk(): void {
    do {
      if (cursor.name === "ImportStatement") {
        const statementFrom = cursor.from;
        const statementTo = cursor.to;
        const modulePaths = parseImportModulePaths();
        for (const modulePath of modulePaths) {
          result.push({ from: statementFrom, to: statementTo, modulePath });
        }
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

export type PythonMemberCall = {
  from: number;
  to: number;
  objectName: string;
  propertyName: string;
  propertyFrom: number;
  propertyTo: number;
};

export function findPythonMemberCalls(state: EditorState): PythonMemberCall[] {
  const tree = syntaxTree(state);
  const cursor = tree.cursor() as unknown as TreeCursorLike;
  const result: PythonMemberCall[] = [];

  function parseMemberExpression(): PythonMemberCall | null {
    if (!cursor.firstChild()) return null;

    let objectName = "";
    let propertyName = "";
    let propertyFrom = cursor.from;
    let propertyTo = cursor.to;

    do {
      if (cursor.name === "VariableName" && !objectName) {
        objectName = state.doc.sliceString(cursor.from, cursor.to);
      } else if (cursor.name === "PropertyName" && !propertyName) {
        propertyName = state.doc.sliceString(cursor.from, cursor.to);
        propertyFrom = cursor.from;
        propertyTo = cursor.to;
      }
    } while (cursor.nextSibling());

    cursor.parent();

    if (!objectName || !propertyName) return null;
    return { from: cursor.from, to: cursor.to, objectName, propertyName, propertyFrom, propertyTo };
  }

  function walk(): void {
    do {
      if (cursorNameIs(cursor, "CallExpression")) {
        if (!cursor.firstChild()) continue;

        let call: PythonMemberCall | null = null;
        do {
          if (cursorNameIs(cursor, "MemberExpression")) {
            call = parseMemberExpression();
            break;
          }
        } while (cursor.nextSibling());

        cursor.parent();
        if (call) result.push(call);

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
