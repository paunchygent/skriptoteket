/**
 * Classroom planner transport-payload normalization.
 *
 * Purpose:
 *   Normalize partially populated planner responses before they enter the
 *   route shell or Pinia store so missing collection fields never crash the
 *   UI during otherwise valid no-classroom flows.
 *
 * Relationships:
 *   - consumed by catalog, lifecycle, and state-support modules
 *   - keeps API-boundary coercion separate from planner UI orchestration
 */

import type {
  ClassWorkspaceSummary,
  DraftHistoryStatus,
  DraftWorkspaceResponse,
  FixedSeatRule,
  PlanDraftSummary,
  RelationshipRule,
  RoomTemplate,
  Roster,
  RosterSmartRulesResponse,
  StudentSeatingPreference,
  TaskEntryOption,
} from "./classroomPlannerTypes";

function cloneArrayOrEmpty<T>(items: readonly T[] | T[] | null | undefined): T[] {
  return Array.isArray(items) ? [...items] : [];
}

function cloneTaskEntryOptions(options: TaskEntryOption[] | null | undefined): TaskEntryOption[] {
  return cloneArrayOrEmpty(options).map((option) => ({ ...option }));
}

function cloneDraftSummaries(
  summaries: PlanDraftSummary[] | null | undefined,
): PlanDraftSummary[] {
  return cloneArrayOrEmpty(summaries).map((summary) => ({ ...summary }));
}

function cloneRelationshipRules(
  rules: RelationshipRule[] | null | undefined,
): RelationshipRule[] {
  return cloneArrayOrEmpty(rules).map((rule) => ({
    ...rule,
    student_ids: cloneArrayOrEmpty(rule.student_ids),
  }));
}

function cloneSeatingPreferences(
  preferences: StudentSeatingPreference[] | null | undefined,
): StudentSeatingPreference[] {
  return cloneArrayOrEmpty(preferences).map((preference) => ({ ...preference }));
}

function cloneFixedSeatRules(rules: FixedSeatRule[] | null | undefined): FixedSeatRule[] {
  return cloneArrayOrEmpty(rules).map((rule) => ({ ...rule }));
}

function normalizeDraftHistoryStatus(
  historyStatus: DraftHistoryStatus | null | undefined,
): DraftHistoryStatus {
  return {
    can_undo: historyStatus?.can_undo ?? false,
    can_redo: historyStatus?.can_redo ?? false,
  };
}

export function normalizeClassroomPlannerRoster(roster: Roster): Roster {
  return {
    ...roster,
    students: cloneArrayOrEmpty(roster.students).map((student) => ({ ...student })),
  };
}

export function normalizeClassroomPlannerTemplate(template: RoomTemplate): RoomTemplate {
  return {
    ...template,
    seats: cloneArrayOrEmpty(template.seats).map((seat) => ({ ...seat })),
    fixtures: cloneArrayOrEmpty(template.fixtures).map((fixture) => ({ ...fixture })),
  };
}

export function normalizeClassroomPlannerSummary(
  summary: ClassWorkspaceSummary,
): ClassWorkspaceSummary {
  return {
    ...summary,
    task_entry_options: cloneTaskEntryOptions(summary.task_entry_options),
    active_grouping_draft: summary.active_grouping_draft
      ? { ...summary.active_grouping_draft }
      : null,
    active_seating_draft: summary.active_seating_draft
      ? { ...summary.active_seating_draft }
      : null,
    grouping_history: cloneDraftSummaries(summary.grouping_history),
    seating_history: cloneDraftSummaries(summary.seating_history),
  };
}

export function normalizeClassroomPlannerWorkspace(
  workspace: DraftWorkspaceResponse,
): DraftWorkspaceResponse {
  return {
    ...workspace,
    draft: { ...workspace.draft },
    roster: normalizeClassroomPlannerRoster(workspace.roster),
    template: workspace.template
      ? normalizeClassroomPlannerTemplate(workspace.template)
      : null,
    groups: cloneArrayOrEmpty(workspace.groups).map((group) => ({ ...group })),
    group_assignments: cloneArrayOrEmpty(workspace.group_assignments).map((assignment) => ({
      ...assignment,
    })),
    seat_assignments: cloneArrayOrEmpty(workspace.seat_assignments).map((assignment) => ({
      ...assignment,
    })),
    history_status: normalizeDraftHistoryStatus(workspace.history_status),
  };
}

export function normalizeClassroomPlannerSmartRules(
  rules: RosterSmartRulesResponse,
): RosterSmartRulesResponse {
  return {
    ...rules,
    seating_preferences: cloneSeatingPreferences(rules.seating_preferences),
    relationship_rules: cloneRelationshipRules(rules.relationship_rules),
    fixed_seat_rules: cloneFixedSeatRules(rules.fixed_seat_rules),
  };
}
