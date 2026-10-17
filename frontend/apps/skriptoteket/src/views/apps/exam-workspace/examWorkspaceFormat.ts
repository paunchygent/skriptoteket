/**
 * Exam workspace time and keyboard labels.
 *
 * Domain purpose:
 *   Render a saved time the way the workspace shows it ("17 okt 14:05") and
 *   a keyboard shortcut in the platform's notation (⌘S on a Mac, Ctrl+S
 *   elsewhere).
 *
 * Relationships:
 *   - Pure helpers for the header, the Öppna list and the export messages.
 */

const SAVED_AT = new Intl.DateTimeFormat("sv-SE", {
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  month: "short",
});

/** "17 okt 14:05"; the month keeps no trailing period. */
export function examWorkspaceSavedAt(iso: string): string {
  const parts = SAVED_AT.formatToParts(new Date(iso));
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((entry) => entry.type === type)?.value ?? "";
  return `${part("day")} ${part("month").replace(".", "")} ${part("hour")}:${part("minute")}`;
}

export function isMacPlatform(): boolean {
  return typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);
}

/** "⌘S" / "⇧⌘Z" on a Mac, "Ctrl+S" / "Ctrl+Shift+Z" elsewhere. */
export function examWorkspaceShortcut(key: string, shift = false, mac = isMacPlatform()): string {
  if (mac) {
    return `${shift ? "⇧" : ""}⌘${key}`;
  }
  return `Ctrl+${shift ? "Shift+" : ""}${key}`;
}
