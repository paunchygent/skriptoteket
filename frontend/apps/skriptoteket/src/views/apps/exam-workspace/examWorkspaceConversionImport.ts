/**
 * Exam workspace conversion import intake (TASK-SKRIPT-40-04-14).
 *
 * Domain purpose:
 *   Classify an import file and read one QTI package at once: through the
 *   signed-in importer when a teacher side is present, through the guest
 *   store's browser draft otherwise. This is one intake with two store
 *   halves; there is no second intake composable.
 *
 * Relationships:
 *   - Used by `useExamWorkspaceConversion`, which owns the conversion
 *     lifecycle that follows a DigiExam or Word import; the QTI lineage this
 *     intake returns opens through the coordinator's entrance.
 */

import type { ExamWorkspaceStore, GuestSlotAdmission } from "./examWorkspaceStore";

/** A DigiExam export (.dxe) is read by its own importer and stays open to every role. */
export function isDigiExamFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(".dxe");
}

/** A QTI package (.zip) is read without AI and stays open to every role. */
export function isQtiPackageFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(".zip");
}

/**
 * Read one QTI package at once: through the signed-in importer when a
 * teacher side is present, through the guest store's browser draft
 * otherwise. The guest write replaces the browser slot only under
 * `admission`, the import's own live authority and edit-lease tab. Returns
 * the opened lineage, or null when neither side can import.
 */
export async function importQtiPackage(
  store: ExamWorkspaceStore,
  file: File,
  courseKey: string | null,
  admission: GuestSlotAdmission,
): Promise<string | null> {
  const teacher = store.teacher;
  if (teacher) {
    const summary = await teacher.importExamWorkspaceQti(file, courseKey);
    return summary.lineage_id;
  }
  const guest = store.guest;
  if (!guest) return null;
  return await guest.startFromQti(file, courseKey, admission);
}
