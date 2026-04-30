/**
 * Dense-tool primitive class contract for shared planner/editor controls.
 *
 * Relationships:
 * - consumed by `UiDense*` components and toolbar/menu wrappers
 * - encodes the PR-0157 size tiers, disabled-state rules, and quiet dense-action styling
 * - freezes a hard small-radius corner language (`4px`) so dense controls stay blocky, not soft
 */

export type DenseActionTone = "default" | "primary" | "danger";
export type DenseActionSize = "icon" | "utility";
export type DenseActionGroupPosition = "single" | "start" | "middle" | "end";
export type DenseStatusTone = "neutral" | "success" | "warning" | "error";

type DenseActionClassOptions = {
  tone?: DenseActionTone;
  size?: DenseActionSize;
  active?: boolean;
  iconOnly?: boolean;
  groupPosition?: DenseActionGroupPosition;
};

type DenseStatusPillClassOptions = {
  tone?: DenseStatusTone;
  interactive?: boolean;
  active?: boolean;
};

type DenseActionValueClassOptions = {
  groupPosition?: DenseActionGroupPosition;
};

export const DENSE_MENU_ITEM_SELECTOR = '[role="menuitem"]:not([disabled])';

export const DENSE_MENU_PANEL_CLASS =
  "border border-navy bg-white shadow-brutal-sm outline-none z-[var(--huleedu-z-tooltip)]";
export const DENSE_ACTION_RADIUS_CLASS = "rounded-[4px]";
export const DENSE_SEGMENTED_SHELL_CLASS = `${DENSE_ACTION_RADIUS_CLASS} border border-navy/15 bg-canvas/50 p-0.5`;
export const DENSE_SEGMENTED_SUBRAIL_SHELL_CLASS =
  `${DENSE_ACTION_RADIUS_CLASS} border border-navy/20 bg-canvas/60 p-px`;
export const DENSE_SEGMENTED_WORKSPACE_SHELL_CLASS =
  `${DENSE_ACTION_RADIUS_CLASS} border border-navy/25 bg-white p-[2px]`;

export const DENSE_MENU_ITEM_BASE_CLASS =
  "flex w-full items-center gap-2 px-3 py-2 text-left text-[11px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-snug transition-colors focus-visible:outline-none focus:bg-canvas hover:bg-canvas disabled:cursor-not-allowed disabled:opacity-50";

export const DENSE_MENU_SECTION_LABEL_CLASS =
  "text-[10px] font-semibold uppercase tracking-wide text-navy/60";

export const DENSE_FORM_INPUT_CLASS =
  `w-full h-[28px] ${DENSE_ACTION_RADIUS_CLASS} border border-navy/30 bg-white px-2.5 text-[11px] text-navy shadow-none leading-none`;

function groupPositionClass(position: DenseActionGroupPosition): string {
  switch (position) {
    case "start":
      return "rounded-l-[4px] rounded-r-none";
    case "middle":
      return "rounded-none";
    case "end":
      return "rounded-r-[4px] rounded-l-none";
    default:
      return DENSE_ACTION_RADIUS_CLASS;
  }
}

function toneClass(tone: DenseActionTone, active: boolean): string {
  switch (tone) {
    case "primary":
      return active
        ? "border-navy bg-navy/90 text-canvas"
        : "border-navy bg-navy text-canvas hover:bg-navy/90";
    case "danger":
      return active
        ? "border-burgundy/40 bg-burgundy/10 text-burgundy"
        : "border-burgundy/30 bg-white text-burgundy hover:bg-burgundy/5";
    default:
      return active
        ? "border-navy/25 bg-canvas text-navy"
        : "border-navy/20 bg-white text-navy hover:bg-canvas/70";
  }
}

function statusToneClass(
  tone: DenseStatusTone,
  active: boolean,
  interactive: boolean,
): string {
  switch (tone) {
    case "success":
      return active || interactive
        ? "border-success/50 bg-success/15 text-success"
        : "border-success/45 bg-success/10 text-success";
    case "warning":
      return active || interactive
        ? "border-warning/60 bg-warning/20 text-navy"
        : "border-warning/50 bg-warning/15 text-navy";
    case "error":
      return active || interactive
        ? "border-error/45 bg-error/15 text-error"
        : "border-error/40 bg-error/10 text-error";
    default:
      return active || interactive
        ? "border-navy/35 bg-canvas text-navy"
        : "border-navy/30 bg-canvas/40 text-navy/70";
  }
}

export function denseActionButtonClass(options: DenseActionClassOptions = {}): string {
  const {
    tone = "default",
    size = "utility",
    active = false,
    iconOnly = false,
    groupPosition = "single",
  } = options;

  const base =
    "inline-flex items-center justify-center gap-1.5 whitespace-nowrap border font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-2 disabled:cursor-not-allowed";
  const sizeClass =
    size === "icon"
      ? "h-9 w-9 p-0 text-[12px]"
      : "h-[28px] px-2.5 py-1 text-[10px]";
  const disabledClass = iconOnly ? "disabled:opacity-40" : "disabled:opacity-50";

  return [
    base,
    sizeClass,
    disabledClass,
    groupPositionClass(groupPosition),
    toneClass(tone, active),
  ].join(" ");
}

export function denseMenuItemClass(tone: DenseActionTone = "default"): string {
  return `${DENSE_MENU_ITEM_BASE_CLASS} ${tone === "danger" ? "text-burgundy" : "text-navy"}`;
}

export function denseStatusPillClass(options: DenseStatusPillClassOptions = {}): string {
  const { tone = "neutral", interactive = false, active = false } = options;

  const base =
    "inline-flex h-[28px] items-center justify-center rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide leading-none";
  const interactiveClass = interactive
    ? "cursor-pointer transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-2"
    : "";

  return [base, interactiveClass, statusToneClass(tone, active, interactive)].join(" ").trim();
}

export function denseActionValueClass(options: DenseActionValueClassOptions = {}): string {
  const { groupPosition = "single" } = options;

  return [
    "inline-flex h-[28px] items-center justify-center border border-navy/20 bg-canvas/40 px-2.5 text-[10px] font-semibold tracking-[var(--huleedu-tracking-label)] leading-none text-navy/70",
    groupPositionClass(groupPosition),
  ].join(" ");
}
