import type {
  TableBodyPlan,
  TableColliderPlan,
  TableRenderNodePlan,
} from "../pinballTablePlanTypes";

export interface CompilerOutput {
  colliders: TableColliderPlan[];
  renderNodes: TableRenderNodePlan[];
  bodies?: TableBodyPlan[];
}

export interface TableElementCompiler<T> {
  compile(spec: T, context: CompilerContext): CompilerOutput;
}

export interface CompilerContext {
  staticBodyId: string;
  ballRestZ: number;
}
