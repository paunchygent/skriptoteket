/**
 * Exam workspace Import box source naming.
 *
 * Expected behavior:
 *   The box heading names the import source each document origin stands for:
 *   "Word" for a Word import, "DigiExam" for a DigiExam import and "QTI" for
 *   a QTI package import, and never names one source after another.
 */

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import type { Pinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import type { NativeExamDocument, NativeExamImportRecord } from "../../../api/examWorkspace";
import { useAuthStore } from "../../../stores/auth";
import { buildFreeTextItem } from "../../../test/examWorkspaceFixtures";
import ExamWorkspaceImportBox from "./ExamWorkspaceImportBox.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";

const RECORD: NativeExamImportRecord = {
  original_wording: { answer_key_text: null, question_text: "Vad är fotosyntes?" },
  steps: [{ chosen_kind: "single_choice", kind: "chosen_type" }],
};

let pinia: Pinia;
beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
  useAuthStore().user = { id: "u1", email: "u@example.test", role: "admin", auth_provider: "local" };
});

function mountBox(origin: NativeExamDocument["origin"]["kind"]) {
  return mount(ExamWorkspaceImportBox, {
    props: {
      item: buildFreeTextItem(1, { import_record: RECORD }),
      origin,
      open: true,
      disabled: false,
    },
    global: {
      plugins: [pinia, examWorkspaceProvidersPlugin()],
    },
  });
}

function sourceNameOf(origin: NativeExamDocument["origin"]["kind"]): string {
  return mountBox(origin).get(".imp__src").text();
}

describe("ExamWorkspaceImportBox source name", () => {
  it("names QTI for a QTI package import", () => {
    expect(sourceNameOf("qti_import")).toBe("· QTI");
  });

  it("keeps Word for a Word import and DigiExam for a DigiExam import", () => {
    expect(sourceNameOf("docx_import")).toBe("· Word");
    expect(sourceNameOf("digiexam_import")).toBe("· DigiExam");
  });

  it("never names one source after another", () => {
    expect(sourceNameOf("qti_import")).not.toContain("Word");
    expect(sourceNameOf("qti_import")).not.toContain("DigiExam");
    expect(sourceNameOf("docx_import")).not.toContain("QTI");
    expect(sourceNameOf("digiexam_import")).not.toContain("QTI");
  });
});
