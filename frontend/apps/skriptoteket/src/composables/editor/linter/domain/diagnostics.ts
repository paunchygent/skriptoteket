import type { FixIntent } from "./fixIntents";

export type DomainSeverity = "error" | "warning" | "info" | "hint";

export type DomainDiagnostic = {
  from: number;
  to: number;
  severity: DomainSeverity;
  source: string;
  message: string;
  fixes?: FixIntent[];
};
