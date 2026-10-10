/**
 * Exam workspace saved-document list behavior.
 *
 * Expected behavior:
 *   Exams that share a file name are told apart by version, saved time, and
 *   an "N av M med samma namn" count, the position in the current list ordered
 *   by latest save, oldest first; a unique name carries no count.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { ExamWorkspaceDocumentSummary } from "../../../api/examWorkspace";
import ExamWorkspaceSavedDocuments from "./ExamWorkspaceSavedDocuments.vue";

function summary(
  lineageId: string,
  name: string,
  savedAt: string,
): ExamWorkspaceDocumentSummary {
  return { lineage_id: lineageId, name, saved_at: savedAt, vault_file_id: "file", version: 1 };
}

describe("ExamWorkspaceSavedDocuments", () => {
  it("numbers exams with the same name by saved time and leaves unique names alone", () => {
    const wrapper = mount(ExamWorkspaceSavedDocuments, {
      props: {
        documents: [
          summary("l-new", "Prov.provdokument.zip", "2026-10-09T10:00:00Z"),
          summary("l-other", "Annat.provdokument.zip", "2026-10-09T09:00:00Z"),
          summary("l-old", "Prov.provdokument.zip", "2026-10-09T08:00:00Z"),
        ],
        isBusy: false,
        isDirty: false,
      },
    });

    expect(wrapper.get('[data-test="exam-workspace-open-l-old"]').text()).toContain(
      "1 av 2 med samma namn",
    );
    expect(wrapper.get('[data-test="exam-workspace-open-l-new"]').text()).toContain(
      "2 av 2 med samma namn",
    );
    expect(wrapper.get('[data-test="exam-workspace-open-l-other"]').text()).not.toContain(
      "med samma namn",
    );
  });
});
