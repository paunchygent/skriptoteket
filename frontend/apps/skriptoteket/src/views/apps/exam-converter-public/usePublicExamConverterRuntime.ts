/**
 * Public Exam Converter runtime state.
 *
 * Domain purpose:
 *   Orchestrate the anonymous upload, polling, manifest, and artifact download
 *   state for the public Exam Converter without coupling presentation
 *   components to backend transport details.
 *
 * Relationships:
 *   - Uses `examConverterPublicApi` for all public backend calls.
 *   - Feeds `ExamConverterUploadPanel` and
 *     `PublicExamConverterJobPanel` with focused view state and actions.
 */

import { computed, ref } from "vue";

import { isApiError } from "../../../api/client";
import { triggerBrowserDownload } from "./browserDownload";
import {
  downloadPublicExamConverterArtifact,
  getPublicExamConverterArtifactManifest,
  getPublicExamConverterStatus,
  submitPublicExamConverterJob,
  type ArtifactEntry,
  type ArtifactManifest,
  type ExamConverterTarget,
  type PublicJobStatus,
  type StatusResponse,
  type SubmitResponse,
} from "./examConverterPublicApi";

const DEFAULT_TARGETS: ExamConverterTarget[] = ["examnet_pdf", "qti_package"];

const STATUS_LABELS: Record<PublicJobStatus, string> = {
  canceled: "Avbruten",
  expired: "Utgången",
  failed: "Misslyckad",
  processing: "Bearbetar",
  queued: "Köad",
  submitted: "Skickad",
  succeeded: "Klar",
};

export function usePublicExamConverterRuntime() {
  const sourceDxeFile = ref<File | null>(null);
  const gradedResultPdfFile = ref<File | null>(null);
  const selectedTargets = ref<ExamConverterTarget[]>([...DEFAULT_TARGETS]);
  const currentJob = ref<SubmitResponse | null>(null);
  const status = ref<StatusResponse | null>(null);
  const manifest = ref<ArtifactManifest | null>(null);
  const isSubmitting = ref(false);
  const isPolling = ref(false);
  const downloadingArtifactKey = ref<string | null>(null);
  const errorMessage = ref<string | null>(null);

  const sourceDxeFileName = computed(() => sourceDxeFile.value?.name ?? null);
  const gradedResultPdfFileName = computed(() => gradedResultPdfFile.value?.name ?? null);

  const canSubmit = computed(() => {
    return (
      sourceDxeFile.value !== null &&
      selectedTargets.value.length > 0 &&
      !isSubmitting.value
    );
  });

  const statusLabel = computed(() => {
    const value = status.value?.status ?? currentJob.value?.status;
    return value ? STATUS_LABELS[value] : "Redo";
  });

  const availableArtifacts = computed(() => {
    return (
      manifest.value?.artifacts.filter(
        (artifact) => artifact.availability === "available",
      ) ?? []
    );
  });

  function setSourceDxeFile(file: File | null): void {
    sourceDxeFile.value = file;
  }

  function setGradedResultPdfFile(file: File | null): void {
    gradedResultPdfFile.value = file;
  }

  function toggleTarget(target: ExamConverterTarget, checked: boolean): void {
    if (checked && !selectedTargets.value.includes(target)) {
      selectedTargets.value = [...selectedTargets.value, target];
      return;
    }

    if (!checked) {
      selectedTargets.value = selectedTargets.value.filter((value) => value !== target);
    }
  }

  async function submitJob(): Promise<void> {
    if (!sourceDxeFile.value) {
      return;
    }

    isSubmitting.value = true;
    errorMessage.value = null;
    manifest.value = null;
    status.value = null;

    try {
      const submitted = await submitPublicExamConverterJob({
        sourceDxe: sourceDxeFile.value,
        gradedResultPdf: gradedResultPdfFile.value,
        targets: selectedTargets.value,
      });
      currentJob.value = submitted;
      status.value = {
        public_job_id: submitted.public_job_id,
        status: submitted.status,
        expires_at: submitted.expires_at,
        error: null,
      };
      await refreshJob();
    } catch (error: unknown) {
      errorMessage.value = toUserFacingError(error);
    } finally {
      isSubmitting.value = false;
    }
  }

  async function refreshJob(): Promise<void> {
    if (!currentJob.value) {
      return;
    }

    isPolling.value = true;
    errorMessage.value = null;

    try {
      const nextStatus = await getPublicExamConverterStatus(currentJob.value.poll_url);
      status.value = nextStatus;
      if (nextStatus.status === "succeeded") {
        manifest.value = await getPublicExamConverterArtifactManifest(
          currentJob.value.artifact_manifest_url,
        );
      }
    } catch (error: unknown) {
      errorMessage.value = toUserFacingError(error);
    } finally {
      isPolling.value = false;
    }
  }

  async function downloadArtifact(artifact: ArtifactEntry): Promise<void> {
    if (!artifact.download_url) {
      return;
    }

    downloadingArtifactKey.value = artifact.artifact_key;
    errorMessage.value = null;

    try {
      const response = await downloadPublicExamConverterArtifact(artifact.download_url);
      triggerBrowserDownload(
        response.blob,
        response.filename ?? artifact.filename ?? artifact.artifact_key,
      );
    } catch (error: unknown) {
      errorMessage.value = toUserFacingError(error);
    } finally {
      downloadingArtifactKey.value = null;
    }
  }

  return {
    availableArtifacts,
    canSubmit,
    currentJob,
    downloadingArtifactKey,
    errorMessage,
    gradedResultPdfFileName,
    isPolling,
    isSubmitting,
    manifest,
    selectedTargets,
    setGradedResultPdfFile,
    setSourceDxeFile,
    sourceDxeFileName,
    status,
    statusLabel,
    submitJob,
    toggleTarget,
    refreshJob,
    downloadArtifact,
  };
}

function toUserFacingError(error: unknown): string {
  if (isApiError(error)) {
    switch (error.status) {
      case 400:
      case 413:
      case 415:
      case 422:
        return "Filen eller målformatet kan inte användas. Kontrollera urvalet och försök igen.";
      case 429:
        return "Det är många konverteringar just nu. Vänta en stund och försök igen.";
      case 503:
        return "Konverteringstjänsten är inte tillgänglig just nu.";
      default:
        return "Konverteringen kunde inte genomföras. Försök igen.";
    }
  }

  return "Konverteringen kunde inte genomföras. Försök igen.";
}
