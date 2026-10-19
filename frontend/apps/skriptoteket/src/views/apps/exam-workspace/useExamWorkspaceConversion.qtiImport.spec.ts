/**
 * Exam workspace QTI package import dispatch.
 *
 * Expected behavior:
 *   A .zip source file goes to the QTI importer with the course key, never
 *   starts the conversion polling of the Word and DigiExam imports, and opens
 *   the returned saved document through the Öppna list's open path once the
 *   import no longer counts as busy. A refusal from the server is shown as
 *   the inline error and the failure toast in its own Swedish wording, and a
 *   failure without a server message falls back to the generic copy.
 */

import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, ref } from "vue";
import type { Ref } from "vue";

import { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useToastStore } from "../../../stores/toast";
import type { ExamWorkspaceConversionBinding } from "./useExamWorkspaceConversion";
import { useExamWorkspaceConversion } from "./useExamWorkspaceConversion";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceConversionStatus: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDigiExam: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceQti: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => apiMocks);

const QTI_SUMMARY = {
  course_key: null,
  lineage_id: "lineage-9",
  name: "Prov_HT25.zip",
  saved_at: "2026-10-18T09:00:00Z",
  title: "Prov HT25",
  vault_file_id: "file-1",
  version: 1,
};

function binding(): ExamWorkspaceConversionBinding {
  return {
    isDirty: ref(false),
    serverDocument: ref<NativeExamDocument | null>(null),
    summary: ref(null) as Ref<ExamWorkspaceDocumentSummary | null>,
    workspaceDocument: ref<NativeExamDocument | null>(null),
    beginDocumentRead: () => (response) => response,
    applyResponse: vi.fn(),
    beforeFirstRevision: vi.fn(),
    isSaving: () => false,
  };
}

function setup() {
  setActivePinia(createPinia());
  const scope = effectScope();
  const busyWhileOpening: { isImporting: boolean | null } = { isImporting: null };
  const openImported = vi.fn(async () => {
    busyWhileOpening.isImporting = conversion?.isImporting.value ?? null;
    return true;
  });
  let conversion: ReturnType<typeof useExamWorkspaceConversion> | null = null;
  conversion = scope.run(() =>
    useExamWorkspaceConversion(() => false, binding(), openImported)
  ) ?? null;
  if (!conversion) throw new Error("expected the composable");
  return { busyWhileOpening, conversion, openImported, scope };
}

function toastMessages(): string[] {
  return useToastStore().toasts.map((toast) => toast.message);
}

function zipFile(): File {
  return new File(["qti"], "Prov_HT25.zip", { type: "application/zip" });
}

beforeEach(() => {
  setActivePinia(createPinia());
  for (const mock of Object.values(apiMocks)) mock.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("QTI .zip import dispatch", () => {
  it("routes a .zip to the QTI importer with the course key and opens the returned lineage", async () => {
    apiMocks.importExamWorkspaceQti.mockResolvedValue(QTI_SUMMARY);
    const { conversion, openImported } = setup();

    await conversion.importDocument(zipFile(), "gy11:SVESVE01");

    expect(apiMocks.importExamWorkspaceQti).toHaveBeenCalledTimes(1);
    const [file, courseKey] = apiMocks.importExamWorkspaceQti.mock.calls[0] as [File, string | null];
    expect(file.name).toBe("Prov_HT25.zip");
    expect(courseKey).toBe("gy11:SVESVE01");
    expect(apiMocks.importExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(apiMocks.importExamWorkspaceDigiExam).not.toHaveBeenCalled();
    expect(openImported).toHaveBeenCalledWith("lineage-9");
  });

  it("opens the saved exam only once the import is no longer busy, and never polls a conversion", async () => {
    apiMocks.importExamWorkspaceQti.mockResolvedValue(QTI_SUMMARY);
    const { busyWhileOpening, conversion } = setup();

    await conversion.importDocument(zipFile(), null);

    expect(busyWhileOpening.isImporting).toBe(false);
    expect(apiMocks.getExamWorkspaceConversionStatus).not.toHaveBeenCalled();
  });

  it("shows the server's Swedish refusal as the inline error and the failure toast, and opens nothing", async () => {
    apiMocks.importExamWorkspaceQti.mockRejectedValue(
      new ApiError({
        code: "QTI_PACKAGE_UNREADABLE",
        message: "Det gick inte att läsa QTI-paketet.",
        status: 422,
      }),
    );
    const { conversion, openImported } = setup();

    await conversion.importDocument(zipFile(), null);

    expect(conversion.conversionError.value).toBe("Det gick inte att läsa QTI-paketet.");
    expect(toastMessages()).toEqual(["Det gick inte att läsa QTI-paketet."]);
    expect(openImported).not.toHaveBeenCalled();
    expect(apiMocks.getExamWorkspaceConversionStatus).not.toHaveBeenCalled();
  });

  it("falls back to the generic failure copy when the failure carries no server message", async () => {
    apiMocks.importExamWorkspaceQti.mockRejectedValue(new Error("network down"));
    const { conversion } = setup();

    await conversion.importDocument(zipFile(), null);

    expect(conversion.conversionError.value).toBe("Det gick inte att läsa in provet. Försök igen.");
    expect(toastMessages()).toEqual(["Det gick inte att läsa in provet. Försök igen."]);
  });

  it("shows no conversion progress for a .zip import", async () => {
    apiMocks.importExamWorkspaceQti.mockResolvedValue(QTI_SUMMARY);
    const { conversion } = setup();

    await conversion.importDocument(zipFile(), null);

    expect(conversion.isConverting.value).toBe(false);
    expect(conversion.conversionProgress.value).toBeNull();
    expect(conversion.conversionMessage.value).toBeNull();
  });
});
