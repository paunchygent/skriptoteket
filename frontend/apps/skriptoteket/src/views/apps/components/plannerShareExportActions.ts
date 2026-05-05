/**
 * Typed planner share/export action model.
 *
 * Relationships:
 * - consumed by the grouped and seating toolbar distribution panels
 * - keeps file-export option types out of visual Vue components
 */

import type { GroupingExportOption, SeatingExportOption } from "../classroomPlannerExportApi";

export type PlannerExportOptionValue = SeatingExportOption | GroupingExportOption;

export type PlannerExportFileOption = {
  id: string;
  label: string;
  option: PlannerExportOptionValue;
  isDefault?: boolean;
};

export type PlannerExportShareOption = {
  id: string;
  label: string;
  action: "share-link";
  isDefault?: false;
};

export type PlannerExportOption = PlannerExportFileOption | PlannerExportShareOption;

export type PlannerShareExportScopeOption = {
  value: string;
  label: string;
  meta?: string | null;
  summary?: {
    contextLabel: string;
    kindLabel: string;
    details?: string[];
  } | null;
  disabled?: boolean;
  disabledReason?: string | null;
};
