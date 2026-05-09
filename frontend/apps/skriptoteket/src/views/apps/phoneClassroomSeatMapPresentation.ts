/**
 * Phone classroom-seat map presentation helpers.
 *
 * This module keeps compact phone seat-label formatting outside the shared map
 * component so touch/viewport behavior can evolve without growing the renderer.
 */

export const PHONE_MAP_BASE_CELL_SIZE_PX = 44;

export type PhoneSeatStudentName = {
  firstName: string;
  lastInitials: string | null;
};

export function formatPhoneSeatStudentName(displayName: string): PhoneSeatStudentName | null {
  const parts = displayName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return null;
  }
  const lastInitials = parts
    .slice(1)
    .map((part) => part[0]?.toLocaleUpperCase("sv-SE") ?? "")
    .filter(Boolean)
    .join("");
  return {
    firstName: parts[0] ?? displayName.trim(),
    lastInitials: lastInitials.length > 0 ? lastInitials : null,
  };
}
