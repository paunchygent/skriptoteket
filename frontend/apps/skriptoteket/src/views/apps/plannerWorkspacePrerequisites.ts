/**
 * Approved prerequisite copy and selector-lock helpers for Klassrumskartan.
 *
 * Relationships:
 * - consumed by the overview shell and live planner shell
 * - locks the exact Swedish prerequisite copy approved for ST-29-10
 */

export const PLANNER_NO_CLASS_GUIDANCE = "Börja med att skapa en klasslista.";
export const PLANNER_NO_CLASS_HINT = "Skapa först en klasslista.";
export const PLANNER_NO_CLASSROOM_GUIDANCE =
  "Nu har du skapat din klass. Skapa eller välj ett klassrum för att använda Sittplatser.";
export const PLANNER_NO_CLASSROOM_HINT = "Skapa eller välj först ett klassrum.";
export const PLANNER_HELP_AFFORDANCE = "Behöver du mer vägledning kan du trycka på Hjälp.";

export type PlannerWorkspaceDisabledReasons = {
  grouping: string | null;
  seating: string | null;
  rules: string | null;
};

export function resolvePlannerWorkspaceDisabledReasons(options: {
  hasRoster: boolean;
  hasTemplate: boolean;
}): PlannerWorkspaceDisabledReasons {
  if (!options.hasRoster) {
    return {
      grouping: PLANNER_NO_CLASS_HINT,
      seating: PLANNER_NO_CLASS_HINT,
      rules: PLANNER_NO_CLASS_HINT,
    };
  }

  if (!options.hasTemplate) {
    return {
      grouping: null,
      seating: PLANNER_NO_CLASSROOM_HINT,
      rules: null,
    };
  }

  return {
    grouping: null,
    seating: null,
    rules: null,
  };
}

export function resolvePlannerOverviewPrerequisiteCopy(options: {
  hasRoster: boolean;
  hasTemplate: boolean;
}): {
  guidance: string | null;
  help: string | null;
} {
  if (!options.hasRoster) {
    return {
      guidance: PLANNER_NO_CLASS_GUIDANCE,
      help: PLANNER_HELP_AFFORDANCE,
    };
  }

  if (!options.hasTemplate) {
    return {
      guidance: PLANNER_NO_CLASSROOM_GUIDANCE,
      help: PLANNER_HELP_AFFORDANCE,
    };
  }

  return {
    guidance: null,
    help: null,
  };
}
