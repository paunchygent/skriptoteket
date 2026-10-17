/**
 * Purpose:
 *     Define dense-tool primitive class builders for shared planner, editor,
 *     and auth-support controls.
 *
 * Relationships:
 *     - Consumed by shared UiDense* Vue components.
 *     - Frozen by manifest primitive metadata for consumer drift checks.
 */

export type DenseActionTone = "default" | "primary" | "secondary" | "danger";
export type DenseActionSize = "icon" | "utility" | "touch";
export type DenseActionGroupPosition = "single" | "start" | "middle" | "end";
export type DenseStatusTone = "neutral" | "success" | "warning" | "error";

export type DenseActionClassOptions = {
  tone?: DenseActionTone;
  size?: DenseActionSize;
  active?: boolean;
  iconOnly?: boolean;
  groupPosition?: DenseActionGroupPosition;
};

export type DenseStatusPillClassOptions = {
  tone?: DenseStatusTone;
  interactive?: boolean;
  active?: boolean;
  compact?: boolean;
};

export type DenseActionValueClassOptions = {
  groupPosition?: DenseActionGroupPosition;
};

export const DENSE_MENU_ITEM_SELECTOR = '[role="menuitem"]:not([disabled])';
export const DENSE_MENU_PANEL_CLASS =
  "border border-navy bg-white shadow-[var(--huleedu-shadow-md)] outline-none z-[var(--huleedu-z-tooltip)]";
export const DENSE_ACTION_RADIUS_CLASS = "rounded-[4px]";
export const DENSE_ICON_SIZE_CLASS = "h-9 w-9";
export const DENSE_TEXT_HEIGHT_CLASS = "h-[28px]";
export const DENSE_COMPACT_SEGMENT_HEIGHT_CLASS = "h-6";
export const DENSE_MODAL_SURFACE_CLASS = "bg-modal";
export const DENSE_PANEL_SURFACE_CLASS = "bg-panel";
export const DENSE_PANEL_MUTED_SURFACE_CLASS = "bg-panel-muted";
export const DENSE_SEGMENTED_SHELL_CLASS =
  `${DENSE_ACTION_RADIUS_CLASS} border border-navy/15 bg-canvas/50 p-0.5`;
export const DENSE_SEGMENTED_SUBRAIL_SHELL_CLASS =
  `${DENSE_ACTION_RADIUS_CLASS} border border-navy/20 bg-canvas/60 p-px`;
export const DENSE_SEGMENTED_WORKSPACE_SHELL_CLASS =
  `${DENSE_ACTION_RADIUS_CLASS} border border-navy/25 bg-white p-[2px]`;
export const DENSE_MENU_ITEM_BASE_CLASS =
  "flex w-full items-center gap-2 px-3 py-2 text-left text-[11px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-snug transition-colors focus-visible:outline-none focus:bg-canvas hover:bg-canvas disabled:cursor-not-allowed disabled:opacity-50";
export const DENSE_MENU_SECTION_LABEL_CLASS =
  "text-[10px] font-semibold uppercase tracking-wide text-navy/60";
export const DENSE_FORM_INPUT_CLASS =
  `w-full ${DENSE_TEXT_HEIGHT_CLASS} ${DENSE_ACTION_RADIUS_CLASS} border border-navy/30 bg-white px-2.5 text-[11px] text-navy shadow-none leading-none`;

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

function toneClass(tone: DenseActionTone, active: boolean, iconOnly: boolean): string {
  // An icon-only delete action is its glyph alone; the border stays for geometry.
  if (tone === "danger" && iconOnly) {
    return active
      ? "border-transparent bg-burgundy/10 text-burgundy"
      : "border-transparent bg-transparent text-burgundy hover:bg-burgundy/5";
  }
  switch (tone) {
    case "primary":
      return active
        ? "border-navy bg-navy/90 text-canvas"
        : "border-navy bg-navy text-canvas hover:bg-navy/90";
    case "secondary":
      return active
        ? "border-action bg-action/10 text-action"
        : "border-action/60 bg-canvas/40 text-action hover:border-action hover:bg-action/5";
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
    "inline-flex items-center justify-center gap-1.5 border font-semibold normal-case tracking-[var(--huleedu-tracking-label)] leading-none transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-2 disabled:cursor-not-allowed";
  const sizeClass =
    size === "touch"
      ? `h-[44px] min-h-[44px] min-w-[44px] shrink-0 ${iconOnly ? "w-[44px] p-0 text-[12px]" : "px-2.5 py-1 text-[10px]"}`
      : size === "icon"
        ? `${DENSE_ICON_SIZE_CLASS} p-0 text-[12px]`
        : `${DENSE_TEXT_HEIGHT_CLASS} px-2.5 py-1 text-[10px]`;
  const disabledClass = iconOnly ? "disabled:opacity-40" : "disabled:opacity-50";

  return [
    base,
    sizeClass,
    disabledClass,
    groupPositionClass(groupPosition),
    toneClass(tone, active, iconOnly),
  ].join(" ");
}

export function denseMenuItemClass(tone: DenseActionTone = "default"): string {
  return `${DENSE_MENU_ITEM_BASE_CLASS} ${tone === "danger" ? "text-burgundy" : "text-navy"}`;
}

export function denseStatusPillClass(options: DenseStatusPillClassOptions = {}): string {
  const { tone = "neutral", interactive = false, active = false, compact = false } = options;
  const base = compact
    ? "inline-flex h-3 w-3 shrink-0 items-center justify-center rounded-full border-0 bg-transparent p-0"
    : "inline-flex h-[28px] items-center justify-center rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide leading-none";
  const interactiveClass = interactive
    ? "cursor-pointer transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-2"
    : "";

  const compactToneClass: Record<DenseStatusTone, string> = {
    neutral: "text-navy/70",
    success: "text-success",
    warning: "text-warning",
    error: "text-error",
  };
  const toneClass = compact ? compactToneClass[tone] : statusToneClass(tone, active, interactive);

  return [base, interactiveClass, toneClass].join(" ").trim();
}

export function denseActionValueClass(options: DenseActionValueClassOptions = {}): string {
  const { groupPosition = "single" } = options;

  return [
    "inline-flex h-[28px] items-center justify-center border border-navy/20 bg-canvas/40 px-2.5 text-[10px] font-semibold tracking-[var(--huleedu-tracking-label)] leading-none text-navy/70",
    groupPositionClass(groupPosition),
  ].join(" ");
}
