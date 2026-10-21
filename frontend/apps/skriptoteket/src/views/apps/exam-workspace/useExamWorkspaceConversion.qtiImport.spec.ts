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
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { effectScope, ref } from "vue";
import type { Ref } from "vue";

import { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useToastStore } from "../../../stores/toast";
import { serverExamWorkspaceStore, type ExamWorkspaceStore } from "./examWorkspaceStore";
import { createSyncFence } from "./examWorkspaceSyncFence";
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
  const fence = createSyncFence();
  return {
    isDirty: ref(false),
    serverDocument: ref<NativeExamDocument | null>(null),
    summary: ref(null) as Ref<ExamWorkspaceDocumentSummary | null>,
    workspaceDocument: ref<NativeExamDocument | null>(null),
    beginDocumentRead: () => (response) => response,
    applyResponse: vi.fn(),
    getFence: () => fence,
    isCurrent: (token) => fence.isCurrent(token),
    isSaving: () => false,
    noteImportStarted: vi.fn(),
    store: serverExamWorkspaceStore,
  };
}

function setup() {
  setActivePinia(createPinia());
  const scope = effectScope();
  const conversionBinding = binding();
  const busyWhileOpening: { isImporting: boolean | null } = { isImporting: null };
  const openImported = vi.fn(async () => {
    busyWhileOpening.isImporting = conversion?.isImporting.value ?? null;
    return "installed" as const;
  });
  let conversion: ReturnType<typeof useExamWorkspaceConversion> | null = null;
  conversion = scope.run(() =>
    useExamWorkspaceConversion(() => false, conversionBinding, openImported)
  ) ?? null;
  if (!conversion) throw new Error("expected the composable");
  return { busyWhileOpening, conversion, noteImportStarted: conversionBinding.noteImportStarted as Mock, openImported, scope };
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

  it("names the imported exam for the import-time points check before opening it (TASK-SKRIPT-40-04-23)", async () => {
    apiMocks.importExamWorkspaceQti.mockResolvedValue(QTI_SUMMARY);
    const { conversion, noteImportStarted, openImported } = setup();

    await conversion.importDocument(zipFile(), null);

    expect(noteImportStarted).toHaveBeenCalledExactlyOnceWith("lineage-9");
    expect(noteImportStarted.mock.invocationCallOrder[0]).toBeLessThan(openImported.mock.invocationCallOrder[0] ?? 0);
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

describe("guest-mode QTI .zip import dispatch", () => {
  function guestSetup() {
    setActivePinia(createPinia());
    const scope = effectScope();
    const busyWhileOpening: { isImporting: boolean | null } = { isImporting: null };
    const startFromQti: Mock<(file: File, courseKey: string | null) => Promise<string>> = vi.fn(
      async (_file: File, _courseKey: string | null) => "lineage-guest",
    );
    const store: ExamWorkspaceStore = {
      guest: { startBlank: vi.fn(async () => "lineage-blank"), startFromQti },
      shared: serverExamWorkspaceStore.shared,
      teacher: null,
    };
    const openImported = vi.fn(async () => {
      busyWhileOpening.isImporting = conversion?.isImporting.value ?? null;
      return "installed" as const;
    });
    let conversion: ReturnType<typeof useExamWorkspaceConversion> | null = null;
    conversion = scope.run(() =>
      useExamWorkspaceConversion(() => false, { ...binding(), store }, openImported)
    ) ?? null;
    if (!conversion) throw new Error("expected the composable");
    return { busyWhileOpening, conversion, openImported, scope, startFromQti };
  }

  it("routes a .zip to guest.startFromQti and opens the lineage, never touching teacher APIs", async () => {
    const { conversion, openImported, startFromQti } = guestSetup();

    await conversion.importDocument(zipFile(), null);

    expect(startFromQti).toHaveBeenCalledTimes(1);
    const [file, courseKey] = startFromQti.mock.calls[0]!;
    expect(file.name).toBe("Prov_HT25.zip");
    expect(courseKey).toBeNull();
    expect(openImported).toHaveBeenCalledWith("lineage-guest");
    expect(apiMocks.importExamWorkspaceQti).not.toHaveBeenCalled();
    expect(apiMocks.importExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(apiMocks.importExamWorkspaceDigiExam).not.toHaveBeenCalled();
    expect(apiMocks.getExamWorkspaceConversionStatus).not.toHaveBeenCalled();
  });

  it("passes the course key to the guest store and opens only once the import is idle", async () => {
    const { busyWhileOpening, conversion, startFromQti } = guestSetup();

    await conversion.importDocument(zipFile(), "gy11:SVESVE01");

    expect(startFromQti).toHaveBeenCalledWith(expect.any(File), "gy11:SVESVE01");
    expect(busyWhileOpening.isImporting).toBe(false);
    expect(conversion.isConverting.value).toBe(false);
  });

  it("shows the server's refusal and opens nothing when the guest parse fails", async () => {
    const { conversion, openImported, startFromQti } = guestSetup();
    startFromQti.mockRejectedValue(
      new ApiError({
        code: "QTI_PACKAGE_UNREADABLE",
        message: "Det gick inte att läsa QTI-paketet.",
        status: 422,
      }),
    );

    await conversion.importDocument(zipFile(), null);

    expect(conversion.conversionError.value).toBe("Det gick inte att läsa QTI-paketet.");
    expect(toastMessages()).toEqual(["Det gick inte att läsa QTI-paketet."]);
    expect(openImported).not.toHaveBeenCalled();
    expect(apiMocks.getExamWorkspaceConversionStatus).not.toHaveBeenCalled();
  });

  it("imports no DigiExam file in guest mode without a teacher side", async () => {
    const { conversion, openImported, startFromQti } = guestSetup();

    await conversion.importDocument(new File(["dxe"], "Prov_HT25.dxe"), null);

    expect(startFromQti).not.toHaveBeenCalled();
    expect(apiMocks.importExamWorkspaceDigiExam).not.toHaveBeenCalled();
    expect(openImported).not.toHaveBeenCalled();
    expect(conversion.isImporting.value).toBe(false);
  });
});
