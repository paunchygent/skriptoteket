/**
 * Exam workspace guest handoff rejection record.
 *
 * Domain purpose:
 *   Remember that Mina filer refused one browser draft for good, keyed by
 *   the draft's cursor. A permanent or vault-full rejection means the server
 *   will never accept this draft snapshot, so the handoff reads the record
 *   before posting and returns the recorded rejection instead of posting the
 *   same cursor again. A newer draft (a new cursor) makes the record stale
 *   and the caller clears that cursor before posting. Removal and success
 *   clear only the record naming their own cursor, so a stale tab never
 *   deletes or overwrites a newer draft's record. Transient and deferred
 *   failures are never recorded here.
 *
 * Relationships:
 *   - Read and written by `useExamWorkspaceGuestHandoff`; removal also runs
 *     at the handoff boundary, so the check and the mutation stay
 *     cursor-owned.
 *   - Guarded like `examWorkspaceColumnSizesStorage`: every localStorage
 *     call is wrapped in try/catch, so invalid JSON, a schema mismatch or a
 *     throwing store reads as null and never throws out.
 */

import { z } from "zod";

export const EXAM_WORKSPACE_GUEST_HANDOFF_REJECTION_STORAGE_KEY =
  "skriptoteket.exam-workspace.guest-handoff-rejection";

const guestHandoffRejectionSchema = z.strictObject({
  cursor: z.string().min(1),
  reason: z.enum(["permanent", "vault_full"]),
});

export type GuestHandoffRejection = z.infer<typeof guestHandoffRejectionSchema>;

export type GuestHandoffRejectionStoragePort = {
  read(): GuestHandoffRejection | null;
  write(value: GuestHandoffRejection): void;
  /** Remove the record only when it names this cursor. */
  clearIf(cursor: string): void;
};

/** Parse the stored value; invalid JSON, a schema mismatch or a throw reads as null. */
function parseStoredGuestHandoffRejection(raw: string | null): GuestHandoffRejection | null {
  if (!raw) {
    return null;
  }
  try {
    const result = guestHandoffRejectionSchema.safeParse(JSON.parse(raw));
    return result.success ? result.data : null;
  } catch {
    return null;
  }
}

/** The production record: one guarded localStorage entry keyed by draft cursor. */
export function createLocalStorageGuestHandoffRejectionStorage(): GuestHandoffRejectionStoragePort {
  return {
    read() {
      try {
        return parseStoredGuestHandoffRejection(
          localStorage.getItem(EXAM_WORKSPACE_GUEST_HANDOFF_REJECTION_STORAGE_KEY),
        );
      } catch {
        return null;
      }
    },
    write(value) {
      try {
        localStorage.setItem(
          EXAM_WORKSPACE_GUEST_HANDOFF_REJECTION_STORAGE_KEY,
          JSON.stringify(value),
        );
      } catch {
        // Storage can be full or blocked; the in-memory handoff still
        // returns the rejection for this visit.
      }
    },
    clearIf(cursor: string) {
      try {
        const current = parseStoredGuestHandoffRejection(
          localStorage.getItem(EXAM_WORKSPACE_GUEST_HANDOFF_REJECTION_STORAGE_KEY),
        );
        if (current !== null && current.cursor === cursor) {
          localStorage.removeItem(EXAM_WORKSPACE_GUEST_HANDOFF_REJECTION_STORAGE_KEY);
        }
      } catch {
        // Storage can be blocked; the stale record simply stays until the
        // next load reads it as the cursor it names.
      }
    },
  };
}

/** A single-slot in-memory record for specs. */
export function createInMemoryGuestHandoffRejectionStorage(): GuestHandoffRejectionStoragePort {
  let stored: GuestHandoffRejection | null = null;
  return {
    read() {
      return stored;
    },
    write(value) {
      stored = { ...value };
    },
    clearIf(cursor: string) {
      if (stored !== null && stored.cursor === cursor) {
        stored = null;
      }
    },
  };
}
