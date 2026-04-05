/**
 * Classroom planner overview capability hints.
 *
 * This module defines the presentation-level capability contract shared by the
 * authenticated and public Klassrumskartan overview shells. The authenticated
 * route shell keeps full authoring behavior, while the public guest shell can
 * reuse the same overview components with explicit disabled reasons instead of
 * silently falling through to owner-scoped orchestration.
 */

export type ClassroomPlannerOverviewActionCapabilities = {
  create_disabled_reason?: string | null;
  edit_disabled_reason?: string | null;
  delete_disabled_reason?: string | null;
};

export type ClassroomPlannerOverviewCapabilities = {
  status_message?: string | null;
  supporting_text?: string | null;
  show_grouping_option?: boolean;
  show_seating_option?: boolean;
  show_rules_option?: boolean;
  show_roster_actions?: boolean;
  show_template_actions?: boolean;
  roster_actions?: ClassroomPlannerOverviewActionCapabilities | null;
  template_actions?: ClassroomPlannerOverviewActionCapabilities | null;
};
