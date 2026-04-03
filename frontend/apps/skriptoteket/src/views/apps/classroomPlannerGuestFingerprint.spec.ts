/**
 * Klassrumskartan guest fingerprint tests.
 *
 * These tests verify that guest snapshot fingerprints are deterministic,
 * stable under object key ordering, and emitted in the widened digest format
 * required for later import receipts and dedupe flows.
 */

import { describe, expect, it } from "vitest";

import {
  createClassroomPlannerGuestContentHash,
  createClassroomPlannerGuestFingerprint,
} from "./classroomPlannerGuestFingerprint";

describe("classroomPlannerGuestFingerprint", () => {
  it("is deterministic and stable under object key ordering", () => {
    const orderedValue = {
      roster: {
        name: "SA24D",
        students: [
          { display_name: "Alice Andersson", local_id: "student-1" },
          { display_name: "Bo Berg", local_id: "student-2" },
        ],
      },
      ui_state: {
        current_screen: "planner",
        planner_initial_view: "rules",
      },
    };
    const reorderedValue = {
      ui_state: {
        planner_initial_view: "rules",
        current_screen: "planner",
      },
      roster: {
        students: [
          { local_id: "student-1", display_name: "Alice Andersson" },
          { local_id: "student-2", display_name: "Bo Berg" },
        ],
        name: "SA24D",
      },
    };

    const firstFingerprint = createClassroomPlannerGuestFingerprint(orderedValue);
    const secondFingerprint = createClassroomPlannerGuestFingerprint(reorderedValue);

    expect(firstFingerprint).toBe(secondFingerprint);
    expect(createClassroomPlannerGuestFingerprint(orderedValue)).toBe(firstFingerprint);
  });

  it("uses the widened sha256 format for fingerprints and content hashes", () => {
    const value = {
      roster_count: 2,
      template_count: 1,
      updated_at: "2026-04-04T08:00:00.000Z",
    };

    expect(createClassroomPlannerGuestFingerprint(value)).toMatch(/^sha256:[0-9a-f]{64}$/);
    expect(createClassroomPlannerGuestContentHash(value)).toMatch(/^sha256:[0-9a-f]{64}$/);
  });
});
