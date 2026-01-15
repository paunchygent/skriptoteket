export type VariableType = "List" | "Dict" | "String" | "Unknown";

export type VariableInfo = {
  name: string;
  type: VariableType;
  assignedAt: number;
  operations: string[];
};

export type ScopeKind = "module" | "function" | "class" | "lambda" | "comprehension";

export type ScopeNode = {
  id: number;
  kind: ScopeKind;
  from: number;
  to: number;
  parent: ScopeNode | null;
};

export type ScopeChain = Map<ScopeNode, Map<string, VariableInfo>>;

export function lookupVariable(chain: ScopeChain, name: string, scopeNode: ScopeNode | null): VariableInfo | null {
  let current = scopeNode;
  while (current) {
    const scopeVars = chain.get(current);
    const found = scopeVars?.get(name) ?? null;
    if (found) return found;
    current = current.parent;
  }
  return null;
}

export function findInnermostScopeAtPos(chain: ScopeChain, pos: number): ScopeNode | null {
  let best: ScopeNode | null = null;
  let bestSize = Number.POSITIVE_INFINITY;

  for (const scope of chain.keys()) {
    if (pos < scope.from || pos > scope.to) continue;
    const size = scope.to - scope.from;
    if (size > bestSize) continue;
    best = scope;
    bestSize = size;
  }

  return best;
}
