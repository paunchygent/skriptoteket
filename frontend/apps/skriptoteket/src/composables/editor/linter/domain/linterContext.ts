import type { DomainDiagnostic } from "./diagnostics";
import type {
  PythonCallExpression,
  PythonDictEntry,
  PythonFunctionDefinition,
  PythonImportBindingsSnapshot,
  PythonImportModule,
  PythonMemberCall,
  PythonNodeRange,
  PythonRaiseStatement,
  PythonReturnStatement,
} from "./pythonFacts";
import type { ScopeChain } from "./variables";

export type LinterContext = {
  text: string;
  facts: {
    syntaxErrors: DomainDiagnostic[];
    imports: PythonImportBindingsSnapshot;
    functions: PythonFunctionDefinition[];
    entrypoint: PythonFunctionDefinition | null;
    calls: PythonCallExpression[];
    returns: PythonReturnStatement[];
    raises: PythonRaiseStatement[];
    importModules: PythonImportModule[];
    memberCalls: PythonMemberCall[];
    variables: ScopeChain;
  };
  pythonLiterals: {
    dictionaryEntries: (dict: { from: number; to: number }) => PythonDictEntry[];
    arrayElements: (array: { from: number; to: number }) => PythonNodeRange[];
  };
};
