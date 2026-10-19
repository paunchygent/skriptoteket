/**
 * @fileoverview Type declarations for the SPA Vitest target wrapper so frontend
 * Vitest specs can exercise the shared CLI logic safely.
 */

export interface VitestArgSplit {
  targets: string[];
  passthrough: string[];
}

export interface VitestTargetResolution {
  patterns: string[];
  specFiles: string[];
  unnameable: string[];
}

export interface VitestRunPlan {
  args: string[];
  include: string[] | null;
}

export const appRoot: string;

export function isExplicitTest(arg: string): boolean;
export function isGlob(arg: string): boolean;
export function normalizeVitestPathArg(arg: string): string;
export function listSpecFiles(patterns: string[]): string[];
export function resolveVitestTarget(target: string): VitestTargetResolution;
export function splitVitestArgs(rawArgs: string[]): Promise<VitestArgSplit>;
export function planVitestRun(rawArgs: string[]): Promise<VitestRunPlan>;
export function resolveVitestBin(): string;
export function main(rawArgs?: string[]): Promise<number>;
