/**
 * Transcript formatter exports and artifact actions.
 *
 * Owns export eligibility, request/refresh state, verified artifacts, and
 * download/save feedback for the transcript host's selected-format actions.
 */

import { computed, ref, type Ref } from "vue";

import {
  downloadConversionHubTranscriptFormatterArtifact,
  saveConversionHubTranscriptFormatterArtifact,
  type TranscriptFormatterArtifactKey,
} from "../../../api/conversionHubTranscriptFormatterArtifactActions";
import {
  type ConversionHubTranscriptFormatterArtifactRef,
  type ConversionHubTranscriptFormatterExportResponse,
  type ConversionHubTranscriptFormatterExportStatus,
  getConversionHubTranscriptFormatterExport,
  requestConversionHubTranscriptFormatterExport,
} from "../../../api/conversionHubTranscriptFormatterExports";
import { triggerBrowserDownload } from "../../../utils/browserDownload";
import {
  formatterArtifactActionState,
  type FormatterArtifactActionState,
  type FormatterArtifactActionStates,
} from "./transcriptFormatterArtifactActions";
import type { useTranscriptSpeakerOverlays } from "./useTranscriptSpeakerOverlays";

type TranscriptFormatterRequestedArtifact =
  ConversionHubTranscriptFormatterArtifactRef["requested_artifact"];
type TranscriptFormatterExportOptions = Pick<
  ReturnType<typeof useTranscriptSpeakerOverlays>,
  "speakerOverlayCoverageComplete" | "speakerOverlayStatus"
> & {
  savedTranscriptId: Readonly<Ref<string | null>>;
  canEditSpeakerOverlays: Readonly<Ref<boolean>>;
};

export function useTranscriptFormatterExports({
  savedTranscriptId,
  canEditSpeakerOverlays,
  speakerOverlayCoverageComplete,
  speakerOverlayStatus,
}: TranscriptFormatterExportOptions) {
  const formatterExportArtifacts = ref<ConversionHubTranscriptFormatterArtifactRef[]>([]);
  const formatterExportStatus = ref<ConversionHubTranscriptFormatterExportStatus>("not_requested");
  const formatterExportErrorMessage = ref<string | null>(null);
  const formatterExportRequestInFlight = ref(false);
  const formatterArtifactActionStates = ref<FormatterArtifactActionStates>({});
  const canRequestFormatterExport = computed(
    () =>
      canEditSpeakerOverlays.value &&
      speakerOverlayCoverageComplete.value &&
      speakerOverlayStatus.value === "saved" &&
      !formatterExportRequestInFlight.value,
  );

  function resetFormatterExportState(): void {
    formatterExportArtifacts.value = [];
    formatterExportStatus.value = "not_requested";
    formatterExportErrorMessage.value = null;
    formatterExportRequestInFlight.value = false;
    formatterArtifactActionStates.value = {};
  }

  function applyFormatterExportState(
    response: ConversionHubTranscriptFormatterExportResponse,
  ): void {
    formatterExportStatus.value = response.status;
    formatterExportArtifacts.value = response.status === "succeeded" ? response.artifacts : [];
    formatterArtifactActionStates.value = {};
    formatterExportErrorMessage.value =
      response.status === "failed"
        ? response.error_message ?? "Filerna kunde inte skapas. Försök igen."
        : null;
  }

  async function requestOrRefreshFormatterExport():
    Promise<ConversionHubTranscriptFormatterExportResponse | null> {
    const transcriptId = savedTranscriptId.value;
    if (!transcriptId || !canRequestFormatterExport.value) return null;
    const shouldRefresh =
      formatterExportStatus.value === "pending" || formatterExportStatus.value === "running";
    if (!shouldRefresh) {
      formatterExportStatus.value = "running";
      formatterExportArtifacts.value = [];
    }
    formatterExportRequestInFlight.value = true;
    formatterExportErrorMessage.value = null;
    try {
      const exportState = shouldRefresh
        ? await getConversionHubTranscriptFormatterExport({ transcriptId })
        : await requestConversionHubTranscriptFormatterExport({ transcriptId });
      applyFormatterExportState(exportState);
      return exportState;
    } catch {
      formatterExportStatus.value = "failed";
      formatterExportErrorMessage.value = "Filerna kunde inte skapas. Försök igen.";
      return null;
    } finally {
      formatterExportRequestInFlight.value = false;
    }
  }

  function artifactForRequestedArtifact(
    requestedArtifact: TranscriptFormatterRequestedArtifact,
  ): ConversionHubTranscriptFormatterArtifactRef | null {
    return (
      formatterExportArtifacts.value.find(
        (artifact) => artifact.requested_artifact === requestedArtifact,
      ) ?? null
    );
  }

  async function ensureFormatterArtifact(
    requestedArtifact: TranscriptFormatterRequestedArtifact,
  ): Promise<ConversionHubTranscriptFormatterArtifactRef | null> {
    const existingArtifact = artifactForRequestedArtifact(requestedArtifact);
    if (existingArtifact) return existingArtifact;
    const exportState = await requestOrRefreshFormatterExport();
    const createdArtifact =
      exportState?.artifacts.find(
        (artifact) => artifact.requested_artifact === requestedArtifact,
      ) ?? null;
    if (createdArtifact) return createdArtifact;
    if (exportState?.status === "pending" || exportState?.status === "running") return null;
    formatterExportStatus.value = "failed";
    formatterExportErrorMessage.value = "Filerna kunde inte skapas. Försök igen.";
    return null;
  }

  function setFormatterArtifactActionState(
    artifactKey: TranscriptFormatterArtifactKey,
    patch: Partial<FormatterArtifactActionState>,
  ): void {
    const current = formatterArtifactActionState(
      formatterArtifactActionStates.value,
      artifactKey,
    );
    formatterArtifactActionStates.value = {
      ...formatterArtifactActionStates.value,
      [artifactKey]: {
        ...current,
        ...patch,
      },
    };
  }

  async function handleDownloadFormatterArtifact(
    requestedArtifact: TranscriptFormatterRequestedArtifact,
  ): Promise<void> {
    const transcriptId = savedTranscriptId.value;
    if (!transcriptId) return;
    const artifact = await ensureFormatterArtifact(requestedArtifact);
    if (!artifact) return;
    setFormatterArtifactActionState(artifact.artifact_key, {
      download: "running",
      save: formatterArtifactActionState(
        formatterArtifactActionStates.value,
        artifact.artifact_key,
      ).save,
    });
    try {
      const response = await downloadConversionHubTranscriptFormatterArtifact({
        artifactKey: artifact.artifact_key,
        transcriptId,
      });
      triggerBrowserDownload(response.blob, response.filename ?? artifact.filename);
      setFormatterArtifactActionState(artifact.artifact_key, { download: "succeeded" });
    } catch {
      setFormatterArtifactActionState(artifact.artifact_key, { download: "failed" });
    }
  }

  async function handleSaveFormatterArtifact(
    requestedArtifact: TranscriptFormatterRequestedArtifact,
  ): Promise<void> {
    const transcriptId = savedTranscriptId.value;
    if (!transcriptId) return;
    const artifact = await ensureFormatterArtifact(requestedArtifact);
    if (!artifact) return;
    setFormatterArtifactActionState(artifact.artifact_key, {
      save: "running",
      savedFilename: null,
    });
    try {
      const saved = await saveConversionHubTranscriptFormatterArtifact({
        artifactKey: artifact.artifact_key,
        transcriptId,
      });
      setFormatterArtifactActionState(artifact.artifact_key, {
        save: "succeeded",
        savedFilename: saved.vault_artifact.name,
      });
    } catch {
      setFormatterArtifactActionState(artifact.artifact_key, { save: "failed" });
    }
  }

  return {
    canRequestFormatterExport,
    formatterArtifactActionStates,
    formatterExportArtifacts,
    formatterExportErrorMessage,
    formatterExportStatus,
    handleDownloadFormatterArtifact,
    handleSaveFormatterArtifact,
    resetFormatterExportState,
  };
}
