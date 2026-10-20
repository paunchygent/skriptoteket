/**
 * Readiness collisions on teacher-made questions (TASK-SKRIPT-39-05-15 D1/D3).
 *
 * Expected behavior:
 *   A teacher-made question (parse_origin teacher_created) never reports the
 *   new reason "unreviewed_retyped_question", even when its review is
 *   required. Two production collisions prove it: an AI Foresla facit
 *   suggestion flips a teacher-made question to review_required with a
 *   machine_proposed key (which reports only
 *   "machine_proposed_key_unreviewed"), and Angra granskad (`unreviewed`)
 *   reopens a teacher-made question without adding the new reason.
 *   Both items are built through the real transitions, never hand-built
 *   review objects.
 */

import { describe, expect, it } from "vitest";

import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import { newTeacherItem, unreviewed } from "./examWorkspaceItemEdits";
import { withArrivingSuggestion } from "./examWorkspaceSuggestionEdits";
import { keyedSuggestion } from "./examWorkspaceKeyedItems.specSupport";

describe("examWorkspaceItemReadiness teacher-made collisions", () => {
  it("an AI suggestion on a teacher-made question reports only the machine-proposed key reason", () => {
    const teacherMade = newTeacherItem("item_001", 1, "single_choice");

    const suggested = withArrivingSuggestion(
      teacherMade,
      keyedSuggestion({ correct_choice_ids: ["choice_001"] }),
    );

    expect(suggested.review.parse_origin).toBe("teacher_created");
    expect(suggested.review.state).toBe("review_required");
    expect(suggested.answer_key.origin).toBe("machine_proposed");

    const reasons = examWorkspaceItemReadiness(suggested);
    expect(reasons).toContain("machine_proposed_key_unreviewed");
    expect(reasons).not.toContain("unreviewed_retyped_question");
  });

  it("Angra granskad on a teacher-made question adds no retyped reason", () => {
    const reopened = unreviewed(newTeacherItem("item_001", 1, "single_choice"));

    expect(reopened.review.parse_origin).toBe("teacher_created");
    expect(reopened.review.state).toBe("review_required");
    expect(examWorkspaceItemReadiness(reopened)).not.toContain("unreviewed_retyped_question");
  });
});
