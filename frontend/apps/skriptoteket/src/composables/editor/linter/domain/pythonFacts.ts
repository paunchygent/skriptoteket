export type PythonNodeRange = {
  name: string;
  from: number;
  to: number;
};

export type PythonDictEntry = {
  key: string;
  keyFrom: number;
  keyTo: number;
  value: PythonNodeRange | null;
};

export type PythonReturnStatement = {
  from: number;
  to: number;
  expression: PythonNodeRange | null;
};

export type PythonRaiseStatement = {
  from: number;
  to: number;
  expression: PythonNodeRange | null;
};

export type PythonImportModule = {
  from: number;
  to: number;
  modulePath: string;
};

export type PythonMemberCall = {
  from: number;
  to: number;
  objectName: string;
  propertyName: string;
  propertyFrom: number;
  propertyTo: number;
};

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

export type PythonImportBindingsSnapshot = {
  moduleBindings: Map<string, string>;
  fromBindings: Map<string, { modulePath: string; importedName: string }>;
};

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
