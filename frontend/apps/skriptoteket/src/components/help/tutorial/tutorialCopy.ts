/**
 * Swedish copy for the Klassrumskartan tutorial clips.
 *
 * Relationships:
 *   - read by `TutorialClipDialog.vue` and `TutorialClipThumbnails.vue`
 */

export const TUTORIAL_COPY = Object.freeze({
  close: "Stäng",
  play: "Spela upp",
  findAgain: "Du hittar klippen igen under Hjälp.",
  loadError: "Klippet kunde inte laddas just nu.",
  moreClips: "Fler klipp",
  thumbnailsLabel: "Klipp",
});

/** Formats a clip duration in whole seconds as m:ss (for example 1:05). */
export function formatClipDuration(totalSeconds: number): string {
  const safeSeconds = Number.isFinite(totalSeconds) ? Math.max(0, Math.round(totalSeconds)) : 0;
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}
