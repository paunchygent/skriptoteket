/**
 * Writing lines on a teacher-added question (TASK-SKRIPT-40-04-07, W4).
 *
 * Expected behavior:
 *   A new free-text question starts at the house default writing area;
 *   every other kind carries no writing area at all.
 */

import { describe, expect, it } from "vitest";

import { newTeacherItem } from "./examWorkspaceItemEdits";
import { DEFAULT_WRITING_LINES } from "./examWorkspaceWritingLines";

describe("newTeacherItem writing lines", () => {
  it("starts a new free-text question at the house default", () => {
    expect(newTeacherItem("item_001", 1, "free_text").writing_lines).toBe(DEFAULT_WRITING_LINES);
  });

  it("gives other kinds no writing area", () => {
    expect(newTeacherItem("item_002", 2, "short_answer").writing_lines).toBeNull();
    expect(newTeacherItem("item_003", 3, "single_choice").writing_lines).toBeNull();
  });
});
