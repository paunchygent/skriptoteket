/**
 * Transcript command button class tokens.
 *
 * Domain purpose:
 *   Keep Audio Transcription operating commands on neutral compact token
 *   surfaces while selector controls own selected-state fill.
 *
 * Relationships:
 *   - Used by transcript workflow rail and formatter export controls.
 *   - Keeps route-local command styling aligned without changing shared
 *     design-system primitives or Document Converter implementation.
 */

const TRANSCRIPT_COMMAND_BUTTON_CLASS_SEGMENTS = [
  "inline-flex h-10 min-w-0 items-center justify-center gap-2 overflow-hidden",
  "rounded-[4px] border border-navy/25 bg-panel px-3 text-xs font-black uppercase leading-none text-navy",
  "transition hover:border-action focus:outline-none",
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action/40",
  "disabled:cursor-not-allowed disabled:border-navy/15 disabled:text-navy/45",
] as const;

export const TRANSCRIPT_COMMAND_BUTTON_CLASS =
  TRANSCRIPT_COMMAND_BUTTON_CLASS_SEGMENTS.join(" ");
