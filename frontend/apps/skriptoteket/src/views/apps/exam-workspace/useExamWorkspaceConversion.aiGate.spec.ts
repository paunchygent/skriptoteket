/**
 * The Öppna drawer's Word import is an AI control (TASK-SKRIPT-REP-0044, L3):
 * only an admin may start the paid DOCX conversion, while the DigiExam importer
 * stays open to every role. The gate runs before any import state changes, so a
 * refused file starts no request and leaves the workspace untouched.
 */

import { createPinia, setActivePinia } from "pinia";
import { effectScope, ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useAuthStore } from "../../../stores/auth";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { createSyncFence } from "./examWorkspaceSyncFence";
import type { ExamWorkspaceRouteOpenOutcome } from "./examWorkspaceReplacementTypes";
import {
  useExamWorkspaceConversion,
  type ExamWorkspaceConversionBinding,
} from "./useExamWorkspaceConversion";

const api = vi.hoisted(() => ({
  getExamWorkspaceConversionStatus: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDigiExam: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceQti: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => ({ ...api }));

type Role = "user" | "contributor" | "admin" | "superuser";

const SUCCEEDED: ExamWorkspaceConversionStatus = {
  job_id: "job-1",
  lineage_id: "lineage-1",
  state: "succeeded",
  error_message: null,
  summary: null,
  document_revision: null,
  questions_total: 0,
  questions_done: 0,
  units: [],
};

const QTI_SUMMARY: ExamWorkspaceDocumentSummary = {
  course_key: null,
  lineage_id: "lineage-1",
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
    summary: ref<ExamWorkspaceDocumentSummary | null>(null),
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

const scopes: Array<{ stop: () => void }> = [];

function conversionFor(role: Role, openImported: (lineageId: string) => Promise<ExamWorkspaceRouteOpenOutcome> = async () => "installed") {
  setActivePinia(createPinia());
  useAuthStore().user = {
    id: "teacher-1",
    email: "teacher@example.test",
    role,
    auth_provider: "local",
  };
  const scope = effectScope();
  scopes.push(scope);
  const conversion = scope.run(() => useExamWorkspaceConversion(() => false, binding(), openImported));
  if (!conversion) throw new Error("conversion did not start");
  return conversion;
}

beforeEach(() => {
  for (const mock of Object.values(api)) mock.mockReset();
  api.importExamWorkspaceDocument.mockResolvedValue(SUCCEEDED);
  api.importExamWorkspaceDigiExam.mockResolvedValue(SUCCEEDED);
  api.importExamWorkspaceQti.mockResolvedValue(QTI_SUMMARY);
  api.getExamWorkspaceConversionStatus.mockResolvedValue(SUCCEEDED);
});

afterEach(() => {
  for (const scope of scopes.splice(0)) scope.stop();
});

describe("exam workspace conversion AI gate", () => {
  it.each<Role>(["user", "contributor"])(
    "refuses a Word .docx for role %s before any import state changes",
    async (role) => {
      const conversion = conversionFor(role);

      await conversion.importDocument(new File(["prov"], "NO_Prov_HT25.docx"), null);

      expect(api.importExamWorkspaceDocument).not.toHaveBeenCalled();
      expect(api.importExamWorkspaceDigiExam).not.toHaveBeenCalled();
      expect(conversion.isImporting.value).toBe(false);
      expect(conversion.conversionStatus.value).toBeNull();
      expect(conversion.conversionError.value).toBeNull();
    },
  );

  it.each<Role>(["user", "contributor", "admin", "superuser"])(
    "still imports a .dxe for role %s",
    async (role) => {
      const conversion = conversionFor(role);

      await conversion.importDocument(new File(["dxe"], "NO_Prov_HT25.dxe"), null);

      expect(api.importExamWorkspaceDigiExam).toHaveBeenCalledTimes(1);
      expect(api.importExamWorkspaceDocument).not.toHaveBeenCalled();
    },
  );

  it("still recognises a DigiExam file by its upper-case extension", async () => {
    const conversion = conversionFor("user");

    await conversion.importDocument(new File(["dxe"], "NO_Prov_HT25.DXE"), null);

    expect(api.importExamWorkspaceDigiExam).toHaveBeenCalledTimes(1);
    expect(api.importExamWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("imports a Word .docx for an admin", async () => {
    const conversion = conversionFor("admin");

    await conversion.importDocument(new File(["prov"], "NO_Prov_HT25.docx"), null);

    expect(api.importExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(api.importExamWorkspaceDigiExam).not.toHaveBeenCalled();
  });

  it("imports a QTI .zip without AI access", async () => {
    const openImported = vi.fn(async () => "installed" as const);
    const conversion = conversionFor("user", openImported);

    await conversion.importDocument(new File(["qti"], "Prov_HT25.zip", { type: "application/zip" }), null);

    expect(api.importExamWorkspaceQti).toHaveBeenCalledTimes(1);
    expect(api.importExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(api.importExamWorkspaceDigiExam).not.toHaveBeenCalled();
    expect(openImported).toHaveBeenCalledWith("lineage-1");
  });

  it("starts no importer for a Word .docx without AI access", async () => {
    const conversion = conversionFor("user");

    await conversion.importDocument(new File(["prov"], "NO_Prov_HT25.docx"), null);

    expect(api.importExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(api.importExamWorkspaceDigiExam).not.toHaveBeenCalled();
    expect(api.importExamWorkspaceQti).not.toHaveBeenCalled();
    expect(conversion.isImporting.value).toBe(false);
  });
});
