/**
 * Session-scoped recovered export notice memory.
 *
 * This helper keeps one-shot planner export completion toasts from reappearing
 * every time the teacher re-enters the same recovered draft in the current
 * browser session. The export flow remains responsible for when to announce;
 * this module only owns the acknowledgement persistence.
 */

const ACKNOWLEDGED_RECOVERED_EXPORT_NOTICES_STORAGE_KEY =
  "skriptoteket:classroom-planner:acknowledged-recovered-export-notices";
const fallbackAcknowledgedRecoveredExportNoticeKeys = new Set<string>();

function getRecoveredExportNoticeStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function readAcknowledgedRecoveredExportNotices(): Set<string> {
  const storage = getRecoveredExportNoticeStorage();
  if (!storage) {
    return new Set(fallbackAcknowledgedRecoveredExportNoticeKeys);
  }
  const raw = storage.getItem(ACKNOWLEDGED_RECOVERED_EXPORT_NOTICES_STORAGE_KEY);
  if (!raw) {
    return new Set();
  }
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      storage.removeItem(ACKNOWLEDGED_RECOVERED_EXPORT_NOTICES_STORAGE_KEY);
      return new Set();
    }
    const acknowledgedKeys = new Set<string>();
    for (const entry of parsed) {
      if (typeof entry === "string") {
        acknowledgedKeys.add(entry);
      }
    }
    return acknowledgedKeys;
  } catch {
    storage.removeItem(ACKNOWLEDGED_RECOVERED_EXPORT_NOTICES_STORAGE_KEY);
    return new Set();
  }
}

export function hasAcknowledgedRecoveredExportNotice(noticeKey: string): boolean {
  return readAcknowledgedRecoveredExportNotices().has(noticeKey);
}

export function markRecoveredExportNoticeAcknowledged(noticeKey: string): void {
  const storage = getRecoveredExportNoticeStorage();
  if (!storage) {
    fallbackAcknowledgedRecoveredExportNoticeKeys.add(noticeKey);
    return;
  }
  const acknowledgedKeys = readAcknowledgedRecoveredExportNotices();
  if (acknowledgedKeys.has(noticeKey)) {
    return;
  }
  acknowledgedKeys.add(noticeKey);
  try {
    storage.setItem(
      ACKNOWLEDGED_RECOVERED_EXPORT_NOTICES_STORAGE_KEY,
      JSON.stringify(Array.from(acknowledgedKeys)),
    );
  } catch {
    fallbackAcknowledgedRecoveredExportNoticeKeys.add(noticeKey);
  }
}
