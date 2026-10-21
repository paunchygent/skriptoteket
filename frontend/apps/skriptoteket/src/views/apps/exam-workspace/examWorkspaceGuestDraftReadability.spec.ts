/**
 * Guest draft readability from the generated format constants (U14, repairs F1).
 *
 * Expected behavior:
 *   A stored draft opens only when every stored document's schema version is
 *   exactly the current native exam document version: the saved copy, the
 *   baseline and every undo step. The browser runs no upgrade steps, so one
 *   older document anywhere makes the whole draft unopenable. A document
 *   without a version string is unopenable too.
 */

import { describe, expect, it } from "vitest";

import {
  CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
  NATIVE_EXAM_DOCUMENT_SCHEMA_PREFIX,
} from "../../../api/nativeExamDocumentVersions.generated";
import {
  newGuestDraft,
  type ExamWorkspaceGuestDraft,
  type ExamWorkspaceGuestDraftIdSource,
} from "./examWorkspaceGuestDraft";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import {
  currentNativeExamDocumentSchemaVersion,
  isGuestDraftReadable,
} from "./examWorkspaceGuestDraftReadability";

const IDS: ExamWorkspaceGuestDraftIdSource = {
  now: () => "2026-10-18T10:00:00.000Z",
  uuid: () => "10000000-0000-4000-8000-000000000001",
};

const CURRENT_TOKEN = '"native_exam_document_v11"';
const OLD_TOKEN = '"native_exam_document_v10"';

/** Downgrade every stored document version token, like a draft saved before v11. */
function downgradeAll(draft: ExamWorkspaceGuestDraft): ExamWorkspaceGuestDraft {
  const downgraded: ExamWorkspaceGuestDraft = JSON.parse(
    JSON.stringify(draft).replaceAll(CURRENT_TOKEN, OLD_TOKEN),
  );
  return downgraded;
}

/** Downgrade only the first stored version token (the baseline), leaving a mixed draft. */
function downgradeFirst(draft: ExamWorkspaceGuestDraft): ExamWorkspaceGuestDraft {
  const downgraded: ExamWorkspaceGuestDraft = JSON.parse(
    JSON.stringify(draft).replace(CURRENT_TOKEN, OLD_TOKEN),
  );
  return downgraded;
}

describe("isGuestDraftReadable", () => {
  it("names the current schema version from the generated constants", () => {
    expect(currentNativeExamDocumentSchemaVersion()).toBe(
      `${NATIVE_EXAM_DOCUMENT_SCHEMA_PREFIX}${CURRENT_NATIVE_EXAM_DOCUMENT_VERSION}`,
    );
  });

  it("opens a fresh current draft", () => {
    const draft = newGuestDraft(buildParentDocument(), IDS, []);

    expect(isGuestDraftReadable(draft)).toBe(true);
  });

  it("refuses a draft saved in the older format", () => {
    const draft = downgradeAll(newGuestDraft(buildParentDocument(), IDS, []));

    expect(isGuestDraftReadable(draft)).toBe(false);
  });

  it("refuses a draft with one older document among current ones", () => {
    const draft = downgradeFirst(newGuestDraft(buildParentDocument(), IDS, []));
    expect(draft.baseline.document.schema_version).not.toBe(
      draft.saved_document.schema_version,
    );

    expect(isGuestDraftReadable(draft)).toBe(false);
  });

  it("refuses a draft saved in an unknown future version", () => {
    const serialized = JSON.stringify(newGuestDraft(buildParentDocument(), IDS, [])).replaceAll(
      CURRENT_TOKEN,
      '"native_exam_document_v12"',
    );
    const draft: ExamWorkspaceGuestDraft = JSON.parse(serialized);

    expect(isGuestDraftReadable(draft)).toBe(false);
  });
});
