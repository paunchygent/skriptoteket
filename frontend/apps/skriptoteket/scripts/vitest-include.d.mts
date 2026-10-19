/**
 * @fileoverview Type declarations for the VITEST_INCLUDE transport shared by
 * the SPA Vitest wrapper and `vitest.config.ts`.
 */

export const VITEST_INCLUDE_ENV: "VITEST_INCLUDE";
export function encodeVitestInclude(include: readonly string[]): string;
export function decodeVitestInclude(value: string | undefined): string[] | null;
