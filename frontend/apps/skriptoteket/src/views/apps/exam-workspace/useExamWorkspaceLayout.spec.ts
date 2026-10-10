/**
 * Exam workspace layout selection.
 *
 * Expected behavior:
 *   Widths from 1024px are desktop, widths from 768px are tablet, and
 *   narrower widths are phone (ADR-SKRIPT-0020 breakpoints).
 */

import { describe, expect, it } from "vitest";

import { resolveExamWorkspaceLayout } from "./useExamWorkspaceLayout";

describe("resolveExamWorkspaceLayout", () => {
  it("selects desktop when the desktop breakpoint matches", () => {
    expect(resolveExamWorkspaceLayout(true, true)).toBe("desktop");
  });

  it("selects tablet between the tablet and desktop breakpoints", () => {
    expect(resolveExamWorkspaceLayout(false, true)).toBe("tablet");
  });

  it("selects phone below the tablet breakpoint", () => {
    expect(resolveExamWorkspaceLayout(false, false)).toBe("phone");
  });
});
