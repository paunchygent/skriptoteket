/**
 * Phone rules tool-row metadata.
 *
 * Purpose:
 *   Keeps the reduced phone `Regler` tool list declarative and reusable
 *   without bloating the workspace shell component.
 *
 * Relationships:
 *   - consumed by `PlannerRulesWorkspacePane.vue`
 *   - uses shared semantic icons from the app icon registry
 */

import type { Component } from "vue";

import {
  IconKeepApart,
  IconKeepNear,
  IconLock,
  IconTeacherAnchor,
} from "../../components/icons";

export type PlannerPhoneRuleToolId = "near_teacher" | "fixed_seat" | "keep_apart" | "keep_near";

export type PlannerPhoneRuleToolRow = {
  id: PlannerPhoneRuleToolId;
  label: string;
  subtitle: string;
  icon: Component;
};

export const PHONE_RULE_TOOL_ROWS: readonly PlannerPhoneRuleToolRow[] = [
  {
    id: "near_teacher",
    label: "Nära läraren",
    subtitle: "Placera elever nära katedern.",
    icon: IconTeacherAnchor,
  },
  {
    id: "fixed_seat",
    label: "Fast plats",
    subtitle: "Lås en elev till en plats.",
    icon: IconLock,
  },
  {
    id: "keep_apart",
    label: "Håll isär",
    subtitle: "Placera elever på avstånd.",
    icon: IconKeepApart,
  },
  {
    id: "keep_near",
    label: "Håll nära",
    subtitle: "Placera elever tillsammans.",
    icon: IconKeepNear,
  },
];
