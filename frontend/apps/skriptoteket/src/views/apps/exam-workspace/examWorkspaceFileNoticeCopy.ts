/**
 * Exam workspace guest handoff notice copy.
 *
 * Domain purpose:
 *   The provisional notice sentences and glyph action names for a browser
 *   draft Mina filer refused (TASK-SKRIPT-41-02-05, pending ui-copy review).
 *
 * Relationships:
 *   - Read by `ExamWorkspaceGuestHandoffNotice` and imported by its spec
 *     and `ExamWorkspaceTeacherHost.spec` so every assertion pins the exact
 *     strings.
 */
export const EXAM_WORKSPACE_GUEST_HANDOFF_PERMANENT_COPY =
  "Provet från webbläsaren kunde inte flyttas till Mina filer. Ladda ner det som en fil eller ta bort det från webbläsaren.";
export const EXAM_WORKSPACE_GUEST_HANDOFF_VAULT_FULL_COPY =
  "Det finns inte plats för provet i Mina filer. Ta bort filer där och försök igen. Du kan också ladda ner provet som fil eller ta bort det från webbläsaren.";
export const EXAM_WORKSPACE_GUEST_HANDOFF_RETRY_NAME = "Försök flytta provet igen";
export const EXAM_WORKSPACE_GUEST_HANDOFF_DOWNLOAD_NAME = "Ladda ner provet som fil";
export const EXAM_WORKSPACE_GUEST_HANDOFF_REMOVE_NAME = "Ta bort provet från webbläsaren";
