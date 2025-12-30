import type { EditorState } from "@codemirror/state";
import { syntaxTree } from "@codemirror/language";

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
