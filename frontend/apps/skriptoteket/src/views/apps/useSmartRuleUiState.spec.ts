import { describe, expect, it } from "vitest";

import { useSmartRuleUiState } from "./useSmartRuleUiState";

describe("useSmartRuleUiState", () => {
  it("clears pending selections when the active tool changes", () => {
    const state = useSmartRuleUiState({
      canEditSmartRules: () => true,
    });

    state.setActiveSeatingSmartTool("keep_near");
    state.togglePendingRelationshipStudent("s1");
    state.togglePendingRelationshipStudent("s2");

    expect(state.pendingRelationshipStudentIds.value).toEqual(["s1", "s2"]);

    state.setActiveSeatingSmartTool("keep_apart");

    expect(state.activeSeatingSmartTool.value).toBe("keep_apart");
    expect(state.pendingRelationshipStudentIds.value).toEqual([]);
  });

  it("only allows relation commits for editable 2+ selections", () => {
    const state = useSmartRuleUiState({
      canEditSmartRules: () => true,
    });

    state.setActiveSeatingSmartTool("keep_near");
    state.togglePendingRelationshipStudent("s1");
    expect(state.canCommitPendingRelationshipRule.value).toBe(false);

    state.togglePendingRelationshipStudent("s2");
    expect(state.canCommitPendingRelationshipRule.value).toBe(true);
  });

  it("allows near-teacher commits after one pending student and tracks edit mode", () => {
    const state = useSmartRuleUiState({
      canEditSmartRules: () => true,
    });

    state.beginNearTeacherEdit(["s1"]);

    expect(state.activeSeatingSmartTool.value).toBe("near_teacher");
    expect(state.pendingRelationshipStudentIds.value).toEqual(["s1"]);
    expect(state.editingNearTeacherRule.value).toBe(true);
    expect(state.canCommitPendingRelationshipRule.value).toBe(true);

    state.clearPendingRelationshipSelection();

    expect(state.editingNearTeacherRule.value).toBe(false);
  });

  it("ignores tool activation when smart rules are not editable", () => {
    const state = useSmartRuleUiState({
      canEditSmartRules: () => false,
    });

    state.setActiveSeatingSmartTool("near_teacher");

    expect(state.activeSeatingSmartTool.value).toBeNull();
  });
});
