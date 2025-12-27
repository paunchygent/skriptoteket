import type { EditorState } from "@codemirror/state";
import { syntaxTree } from "@codemirror/language";

import type { PythonNodeRange } from "./skriptoteketPythonTree";

export type PythonImportBindingsSnapshot = {
  moduleBindings: Map<string, string>;
  fromBindings: Map<string, { modulePath: string; importedName: string }>;
};

export function buildPythonImportBindingsSnapshot(state: EditorState): PythonImportBindingsSnapshot {
  type TreeCursorLike = {
    name: string;
    from: number;
    to: number;
    firstChild: () => boolean;
    nextSibling: () => boolean;
    parent: () => boolean;
  };

  const moduleBindings = new Map<string, string>();
  const fromBindings = new Map<string, { modulePath: string; importedName: string }>();
  const tree = syntaxTree(state);
  const cursor = tree.cursor() as unknown as TreeCursorLike;

  function parseImportStatement(): void {
    if (!cursor.firstChild()) return;

    const statementKind = cursor.name;

    if (statementKind === "import") {
      let moduleParts: string[] = [];
      let alias: string | null = null;
      let awaitingAlias = false;

      while (cursor.nextSibling()) {
        if (cursor.name === "(" || cursor.name === ")") continue;

        if (cursor.name === ",") {
          const modulePath = moduleParts.join("");
          if (modulePath) {
            const localName = alias ?? modulePath.split(".")[0] ?? modulePath;
            moduleBindings.set(localName, modulePath);
          }
          moduleParts = [];
          alias = null;
          awaitingAlias = false;
          continue;
        }

        if (cursor.name === "as") {
          awaitingAlias = true;
          continue;
        }

        if (awaitingAlias && cursor.name === "VariableName") {
          alias = state.doc.sliceString(cursor.from, cursor.to);
          awaitingAlias = false;
          continue;
        }

        if (cursor.name === "VariableName") {
          moduleParts.push(state.doc.sliceString(cursor.from, cursor.to));
        } else if (cursor.name === ".") {
          moduleParts.push(".");
        }
      }

      const modulePath = moduleParts.join("");
      if (modulePath) {
        const localName = alias ?? modulePath.split(".")[0] ?? modulePath;
        moduleBindings.set(localName, modulePath);
      }

      cursor.parent();
      return;
    }

    if (statementKind === "from") {
      const moduleParts: string[] = [];
      let modulePath = "";
      let inModule = true;
      let currentName: { name: string; from: number; to: number } | null = null;
      let currentAlias: string | null = null;
      let awaitingAlias = false;

      while (cursor.nextSibling()) {
        if (inModule && cursor.name === "import") {
          modulePath = moduleParts.join("");
          inModule = false;
          continue;
        }

        if (inModule) {
          if (cursor.name === "VariableName") {
            moduleParts.push(state.doc.sliceString(cursor.from, cursor.to));
          } else if (cursor.name === ".") {
            moduleParts.push(".");
          }
          continue;
        }

        if (cursor.name === "(" || cursor.name === ")") continue;

        if (cursor.name === ",") {
          if (currentName) {
            const localName = currentAlias ?? currentName.name;
            fromBindings.set(localName, { modulePath, importedName: currentName.name });
          }
          currentName = null;
          currentAlias = null;
          awaitingAlias = false;
          continue;
        }

        if (cursor.name === "as") {
          awaitingAlias = true;
          continue;
        }

        if (awaitingAlias && cursor.name === "VariableName" && currentName) {
          currentAlias = state.doc.sliceString(cursor.from, cursor.to);
          awaitingAlias = false;
          continue;
        }

        if (cursor.name === "VariableName" && !currentName) {
          currentName = {
            name: state.doc.sliceString(cursor.from, cursor.to),
            from: cursor.from,
            to: cursor.to,
          };
          continue;
        }
      }

      if (currentName) {
        const localName = currentAlias ?? currentName.name;
        fromBindings.set(localName, { modulePath, importedName: currentName.name });
      }

      cursor.parent();
      return;
    }

    cursor.parent();
  }

  function walk(): void {
    do {
      if (cursor.name === "ImportStatement") {
        parseImportStatement();
        continue;
      }

      if (cursor.firstChild()) {
        walk();
        cursor.parent();
      }
    } while (cursor.nextSibling());
  }

  walk();
  return { moduleBindings, fromBindings };
}

export type PythonKeywordArgument = {
  name: string;
  nameFrom: number;
  nameTo: number;
  value: PythonNodeRange | null;
};

export type PythonCallCallee =
  | { kind: "variable"; name: string; nameFrom: number; nameTo: number }
  | {
      kind: "member";
      objectName: string;
      propertyName: string;
      propertyFrom: number;
      propertyTo: number;
      from: number;
      to: number;
    };

export type PythonCallExpression = {
  from: number;
  to: number;
  callee: PythonCallCallee;
  positionalArgs: PythonNodeRange[];
  keywordArgs: PythonKeywordArgument[];
};

export function findPythonCallExpressions(
  state: EditorState,
  range: { from: number; to: number },
): PythonCallExpression[] {
  type TreeCursorLike = {
    name: string;
    from: number;
    to: number;
    firstChild: () => boolean;
    nextSibling: () => boolean;
    parent: () => boolean;
  };

  const tree = syntaxTree(state);
  const cursor = tree.cursor() as unknown as TreeCursorLike;
  const result: PythonCallExpression[] = [];

  function parseMemberExpression(): Omit<Extract<PythonCallCallee, { kind: "member" }>, "kind"> | null {
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

    if (!propertyName) return null;
    return { from: cursor.from, to: cursor.to, objectName, propertyName, propertyFrom, propertyTo };
  }

  function parseArgList(): { positionalArgs: PythonNodeRange[]; keywordArgs: PythonKeywordArgument[] } {
    const positionalArgs: PythonNodeRange[] = [];
    const keywordArgs: PythonKeywordArgument[] = [];

    if (!cursor.firstChild()) return { positionalArgs, keywordArgs };

    let pendingVar: { name: string; from: number; to: number } | null = null;
    let expectingKeywordValue = false;
    let keywordName: { name: string; from: number; to: number } | null = null;

    do {
      if (cursor.name === "(" || cursor.name === ")" || cursor.name === ",") continue;

      if (expectingKeywordValue && keywordName) {
        keywordArgs.push({
          name: keywordName.name,
          nameFrom: keywordName.from,
          nameTo: keywordName.to,
          value: { name: cursor.name, from: cursor.from, to: cursor.to },
        });
        expectingKeywordValue = false;
        keywordName = null;
        continue;
      }

      if (cursor.name === "AssignOp" && pendingVar) {
        keywordName = pendingVar;
        pendingVar = null;
        expectingKeywordValue = true;
        continue;
      }

      if (cursor.name === "VariableName") {
        if (pendingVar) {
          positionalArgs.push({ name: "VariableName", from: pendingVar.from, to: pendingVar.to });
        }

        pendingVar = {
          name: state.doc.sliceString(cursor.from, cursor.to),
          from: cursor.from,
          to: cursor.to,
        };
        continue;
      }

      if (pendingVar) {
        positionalArgs.push({ name: "VariableName", from: pendingVar.from, to: pendingVar.to });
        pendingVar = null;
      }

      positionalArgs.push({ name: cursor.name, from: cursor.from, to: cursor.to });
    } while (cursor.nextSibling());

    cursor.parent();

    if (pendingVar) {
      positionalArgs.push({ name: "VariableName", from: pendingVar.from, to: pendingVar.to });
    }

    if (expectingKeywordValue && keywordName) {
      keywordArgs.push({ name: keywordName.name, nameFrom: keywordName.from, nameTo: keywordName.to, value: null });
    }

    return { positionalArgs, keywordArgs };
  }

  function parseCallExpression(): PythonCallExpression | null {
    const callFrom = cursor.from;
    const callTo = cursor.to;
    if (!cursor.firstChild()) return null;

    let callee: PythonCallCallee | null = null;
    let positionalArgs: PythonNodeRange[] = [];
    let keywordArgs: PythonKeywordArgument[] = [];

    do {
      if (!callee && cursor.name === "MemberExpression") {
        const parsed = parseMemberExpression();
        if (parsed) callee = { kind: "member", ...parsed };
        continue;
      }

      if (!callee && cursor.name === "VariableName") {
        callee = {
          kind: "variable",
          name: state.doc.sliceString(cursor.from, cursor.to),
          nameFrom: cursor.from,
          nameTo: cursor.to,
        };
        continue;
      }

      if (cursor.name === "ArgList") {
        const parsed = parseArgList();
        positionalArgs = parsed.positionalArgs;
        keywordArgs = parsed.keywordArgs;
      }
    } while (cursor.nextSibling());

    cursor.parent();

    if (!callee) return null;
    return { from: callFrom, to: callTo, callee, positionalArgs, keywordArgs };
  }

  function walk(): void {
    do {
      if (cursor.to < range.from) continue;
      if (cursor.from > range.to) return;

      if (cursor.name === "CallExpression") {
        const parsed = parseCallExpression();
        if (parsed) result.push(parsed);

        if (cursor.firstChild()) {
          walk();
          cursor.parent();
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
