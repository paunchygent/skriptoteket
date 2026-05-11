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

  it("activates the near-teacher tool as a blank authoring state", () => {
    const state = useSmartRuleUiState({
      canEditSmartRules: () => true,
    });

    state.setActiveSeatingSmartTool("near_teacher");

    expect(state.activeSeatingSmartTool.value).toBe("near_teacher");
    expect(state.pendingRelationshipStudentIds.value).toEqual([]);
    expect(state.editingNearTeacherRule.value).toBe(false);
  });

  it("clears candidate students without dropping edit identity", () => {
    const state = useSmartRuleUiState({
      canEditSmartRules: () => true,
    });

    state.beginRelationshipRuleEdit("rule-1", "keep_near", ["s1", "s2"]);

    state.clearPendingRuleCandidates();

    expect(state.activeSeatingSmartTool.value).toBe("keep_near");
    expect(state.pendingRelationshipStudentIds.value).toEqual([]);
    expect(state.editingRelationshipRuleId.value).toBe("rule-1");

    state.togglePendingRelationshipStudent("s3");

    expect(state.pendingRelationshipStudentIds.value).toEqual(["s3"]);
    expect(state.editingRelationshipRuleId.value).toBe("rule-1");
  });

  it("removes a candidate idempotently without dropping edit identity", () => {
    const state = useSmartRuleUiState({
      canEditSmartRules: () => true,
    });

    state.beginRelationshipRuleEdit("rule-1", "keep_near", ["s1", "s2"]);

    state.removePendingRuleCandidate("s1");
    state.removePendingRuleCandidate("s1");

    expect(state.pendingRelationshipStudentIds.value).toEqual(["s2"]);
    expect(state.editingRelationshipRuleId.value).toBe("rule-1");
    expect(state.activeSeatingSmartTool.value).toBe("keep_near");
  });

  it("ignores tool activation when smart rules are not editable", () => {
    const state = useSmartRuleUiState({
      canEditSmartRules: () => false,
    });

    state.setActiveSeatingSmartTool("near_teacher");

    expect(state.activeSeatingSmartTool.value).toBeNull();
  });
});
