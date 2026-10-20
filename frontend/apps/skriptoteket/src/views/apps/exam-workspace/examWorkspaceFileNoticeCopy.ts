/**
 * Exam workspace shared file notice copy.
 *
 * Domain purpose:
 *   The shared notice sentences and glyph action names for a browser
 *   draft Mina filer refused (TASK-SKRIPT-41-02-05, C1-C10 approved,
 *   S1-S6 pending ui-copy review) and for a saved exam the app cannot
 *   read (TASK-SKRIPT-41-02-06, S1-S6 pending ui-copy review).
 *
 * Relationships:
 *   - Read by `ExamWorkspaceFileNotice` and imported by its spec
 *     and `ExamWorkspaceTeacherHost.spec` so every assertion pins the exact
 *     strings.
 */
export const EXAM_WORKSPACE_FILE_NOTICE_GUEST_PERMANENT_COPY =
  "Provet från webbläsaren kunde inte flyttas till Mina filer. Ladda ner det som en fil eller ta bort det från webbläsaren.";
export const EXAM_WORKSPACE_FILE_NOTICE_GUEST_VAULT_FULL_COPY =
  "Det finns inte plats för provet i Mina filer. Ta bort filer där och försök igen. Du kan också ladda ner provet som fil eller ta bort det från webbläsaren.";
export const EXAM_WORKSPACE_FILE_NOTICE_GUEST_UNREADABLE_COPY =
  "Provet är sparat i ett äldre format och kan inte öppnas. Ladda ner det som en fil eller ta bort det från webbläsaren.";
export const EXAM_WORKSPACE_FILE_NOTICE_RETRY_NAME = "Försök flytta provet igen";
export const EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_NAME = "Ladda ner provet som fil";
export const EXAM_WORKSPACE_FILE_NOTICE_GUEST_REMOVE_NAME = "Ta bort provet från webbläsaren";
export const EXAM_WORKSPACE_FILE_NOTICE_SAVED_UNREADABLE_COPY =
  "Provet är sparat i ett äldre format och kan inte öppnas. Ladda ner det som en fil eller ta bort det från Mina filer.";
export const EXAM_WORKSPACE_FILE_NOTICE_SAVED_REMOVE_NAME = "Flytta provet till papperskorgen";
export const EXAM_WORKSPACE_FILE_NOTICE_SAVED_REMOVED_COPY = "Provet flyttades till papperskorgen.";
export const EXAM_WORKSPACE_FILE_NOTICE_REMOVE_FAILURE_COPY =
  "Det gick inte att ta bort provet. Försök igen.";
export const EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_FAILURE_COPY =
  "Det gick inte att ladda ner provet. Försök igen.";
