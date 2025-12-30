import type { EditorState } from "@codemirror/state";
import { syntaxTree } from "@codemirror/language";

import type { ScopeChain, ScopeKind, ScopeNode, VariableInfo, VariableType } from "../domain/variables";

export function buildScopedVariableTable(
  state: EditorState,
  tree: ReturnType<typeof syntaxTree> = syntaxTree(state),
): { chain: ScopeChain; moduleScope: ScopeNode; scopes: readonly ScopeNode[] } {
  type TreeCursorLike = {
    name: string;
    from: number;
    to: number;
    firstChild: () => boolean;
    nextSibling: () => boolean;
    parent: () => boolean;
  };

  function inferTypeFromNodeName(name: string | null): VariableType {
    if (name === "ArrayExpression") return "List";
    if (name === "DictionaryExpression") return "Dict";
    if (name === "String") return "String";
    return "Unknown";
  }

  const listMutators = new Set(["append", "extend", "insert"]);
  const dictMutators = new Set(["update"]);

  const chain: ScopeChain = new Map();
  const moduleScope: ScopeNode = {
    id: 0,
    kind: "module",
    from: 0,
    to: state.doc.length,
    parent: null,
  };

  const moduleVars = new Map<string, VariableInfo>();
  chain.set(moduleScope, moduleVars);

  const scopes: ScopeNode[] = [moduleScope];
  const scopeStack: ScopeNode[] = [moduleScope];
  let nextScopeId = 1;

  function currentScope(): ScopeNode {
    return scopeStack[scopeStack.length - 1] ?? moduleScope;
  }

  function nearestNonClassScope(): ScopeNode {
    for (let i = scopeStack.length - 1; i >= 0; i -= 1) {
      const scope = scopeStack[i];
      if (scope && scope.kind !== "class") return scope;
    }
    return moduleScope;
  }

  function enterScope(kind: Exclude<ScopeKind, "module">, from: number, to: number): ScopeNode {
    const node: ScopeNode = {
      id: nextScopeId,
      kind,
      from,
      to,
      parent: nearestNonClassScope(),
    };
    nextScopeId += 1;

    chain.set(node, new Map());
    scopes.push(node);
    scopeStack.push(node);
    return node;
  }

  function exitScope(): void {
    scopeStack.pop();
  }

  function ensureVariable(scope: ScopeNode, name: string, pos: number): VariableInfo {
    const scopeVars = chain.get(scope);
    if (!scopeVars) throw new Error(`Scope not registered: ${scope.kind}#${scope.id}`);

    const existing = scopeVars.get(name);
    if (existing) return existing;

    const created: VariableInfo = {
      name,
      type: "Unknown",
      assignedAt: pos,
      operations: [],
    };
    scopeVars.set(name, created);
    return created;
  }

  function resolveScopeForName(start: ScopeNode, name: string): ScopeNode | null {
    let current: ScopeNode | null = start;
    while (current) {
      const scopeVars = chain.get(current);
      if (scopeVars?.has(name)) return current;
      current = current.parent;
    }
    return null;
  }

  function recordAssignment(scope: ScopeNode, name: string, pos: number, type: VariableType): void {
    const info = ensureVariable(scope, name, pos);
    info.type = type;
    info.assignedAt = pos;
  }

  function recordOperation(
    scope: ScopeNode,
    name: string,
    operation: string,
    pos: number,
    impliedType: Exclude<VariableType, "Unknown">,
  ): void {
    const resolvedScope = resolveScopeForName(scope, name) ?? scope;
    const info = ensureVariable(resolvedScope, name, pos);
    if (info.type === "Unknown") info.type = impliedType;
    if (!info.operations.includes(operation)) info.operations.push(operation);
  }

  function recordParamsFromCurrentParamList(scope: ScopeNode, cursor: TreeCursorLike): void {
    if (!cursor.firstChild()) return;

    do {
      if (cursor.name !== "VariableName") continue;
      const paramName = state.doc.sliceString(cursor.from, cursor.to);
      recordAssignment(scope, paramName, cursor.from, "Unknown");
    } while (cursor.nextSibling());

    cursor.parent();
  }

  function recordParamsFromCurrentFunctionLikeNode(scope: ScopeNode, cursor: TreeCursorLike): void {
    if (!cursor.firstChild()) return;

    do {
      if (cursor.name === "ParamList") {
        recordParamsFromCurrentParamList(scope, cursor);
      }
    } while (cursor.nextSibling());

    cursor.parent();
  }

  function recordAssignmentFromCurrentAssignStatement(scope: ScopeNode, cursor: TreeCursorLike): void {
    if (!cursor.firstChild()) return;

    let target: { name: string; from: number } | null = null;
    let valueNodeName: string | null = null;

    do {
      if (!target && cursor.name === "VariableName") {
        target = { name: state.doc.sliceString(cursor.from, cursor.to), from: cursor.from };
        continue;
      }

      if (!target) continue;
      if (cursor.name === "AssignOp") continue;

      valueNodeName = cursor.name;
      break;
    } while (cursor.nextSibling());

    cursor.parent();

    if (!target) return;
    recordAssignment(scope, target.name, target.from, inferTypeFromNodeName(valueNodeName));
  }

  function parseMemberExpression(cursor: TreeCursorLike): {
    objectName: string;
    objectFrom: number;
    propertyName: string;
  } | null {
    if (!cursor.firstChild()) return null;

    let objectName = "";
    let objectFrom = cursor.from;
    let propertyName = "";

    do {
      if (cursor.name === "VariableName" && !objectName) {
        objectName = state.doc.sliceString(cursor.from, cursor.to);
        objectFrom = cursor.from;
        continue;
      }

      if (cursor.name === "PropertyName" && !propertyName) {
        propertyName = state.doc.sliceString(cursor.from, cursor.to);
      }
    } while (cursor.nextSibling());

    cursor.parent();

    if (!objectName || !propertyName) return null;
    return { objectName, objectFrom, propertyName };
  }

  function recordOperationFromCurrentCallExpression(scope: ScopeNode, cursor: TreeCursorLike): void {
    if (!cursor.firstChild()) return;

    do {
      if (cursor.name !== "MemberExpression") continue;

      const parsed = parseMemberExpression(cursor);
      if (!parsed) break;

      if (listMutators.has(parsed.propertyName)) {
        recordOperation(scope, parsed.objectName, parsed.propertyName, parsed.objectFrom, "List");
      } else if (dictMutators.has(parsed.propertyName)) {
        recordOperation(scope, parsed.objectName, parsed.propertyName, parsed.objectFrom, "Dict");
      }

      break;
    } while (cursor.nextSibling());

    cursor.parent();
  }

  function isComprehensionNode(name: string): boolean {
    return name.endsWith("ComprehensionExpression");
  }

  const cursor = tree.cursor() as unknown as TreeCursorLike;

  function walk(): void {
    do {
      if (cursor.name === "FunctionDefinition") {
        const fnScope = enterScope("function", cursor.from, cursor.to);
        recordParamsFromCurrentFunctionLikeNode(fnScope, cursor);

        if (cursor.firstChild()) {
          walk();
          cursor.parent();
        }

        exitScope();
        continue;
      }

      if (cursor.name === "ClassDefinition") {
        enterScope("class", cursor.from, cursor.to);

        if (cursor.firstChild()) {
          walk();
          cursor.parent();
        }

        exitScope();
        continue;
      }

      if (cursor.name === "LambdaExpression") {
        const lambdaScope = enterScope("lambda", cursor.from, cursor.to);
        recordParamsFromCurrentFunctionLikeNode(lambdaScope, cursor);

        if (cursor.firstChild()) {
          walk();
          cursor.parent();
        }

        exitScope();
        continue;
      }

      if (isComprehensionNode(cursor.name)) {
        enterScope("comprehension", cursor.from, cursor.to);

        if (cursor.firstChild()) {
          walk();
          cursor.parent();
        }

        exitScope();
        continue;
      }

      const scope = currentScope();
      if (cursor.name === "AssignStatement") {
        recordAssignmentFromCurrentAssignStatement(scope, cursor);
      } else if (cursor.name === "CallExpression") {
        recordOperationFromCurrentCallExpression(scope, cursor);
      }

      if (cursor.firstChild()) {
        walk();
        cursor.parent();
      }
    } while (cursor.nextSibling());
  }

  walk();

  return {
    chain,
    moduleScope,
    scopes,
  };
}
