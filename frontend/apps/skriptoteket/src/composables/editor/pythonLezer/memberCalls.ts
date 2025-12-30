import type { EditorState } from "@codemirror/state";
import { syntaxTree } from "@codemirror/language";

type TreeCursorLike = {
  name: string;
  from: number;
  to: number;
  firstChild: () => boolean;
  nextSibling: () => boolean;
  parent: () => boolean;
};

function cursorNameIs(cursor: TreeCursorLike, name: string): boolean {
  return cursor.name === name;
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
