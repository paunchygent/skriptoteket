/**
 * @fileoverview Type declarations for the SPA Vitest path-normalization wrapper
 * so frontend Vitest specs can exercise the shared CLI logic safely.
 */

export function isExplicitTest(arg: string): boolean;
export function isGlob(arg: string): boolean;
export function normalizeVitestPathArg(arg: string): string;
export function expandVitestTarget(arg: string): string[];
export function normalizeVitestArgs(args: string[]): string[];
export function collectVitestTargets(args: string[]): string[];
export function main(rawArgs?: string[]): number;
