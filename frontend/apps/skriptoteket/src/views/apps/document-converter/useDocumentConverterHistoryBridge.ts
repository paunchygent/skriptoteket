/**
 * Bridge preview/job outcomes into Document Converter route-session history.
 *
 * Domain purpose:
 *   Convert backend-backed preview and conversion outcomes into teacher-facing
 *   route-session history entries while keeping raw backend identifiers inside
 *   retry/download/save callbacks.
 *
 * Relationships:
 *   - Used by `DocumentConverterView.vue`.
 *   - Watches `useDocumentConverterProjectPreview` and
 *     `useDocumentConverterSingleFile`.
 *   - Writes entries into `useDocumentConverterSessionHistory`.
 */

import { watch, type Ref } from "vue";

import { triggerBrowserDownload } from "../exam-converter/browserDownload";
import {
  downloadDocumentConverterJobArtifact,
  saveDocumentConverterJobArtifact,
} from "./documentConverterFileApi";
import {
  downloadDocumentConverterProjectPreviewArtifact,
  loadDocumentConverterProjectPreviewArtifactBlob,
  saveDocumentConverterProjectPreviewArtifact,
} from "./documentConverterProjectPreviewApi";
import { useDocumentConverterProjectPreview } from "./useDocumentConverterProjectPreview";
import { useDocumentConverterSessionHistory } from "./useDocumentConverterSessionHistory";
import { useDocumentConverterSingleFile } from "./useDocumentConverterSingleFile";

type WorkspaceMode = "project_preview" | "single_file";

export function useDocumentConverterHistoryBridge(args: {
  workspaceMode: Ref<WorkspaceMode>;
  project: ReturnType<typeof useDocumentConverterProjectPreview>;
  singleFile: ReturnType<typeof useDocumentConverterSingleFile>;
  projectHistory: ReturnType<typeof useDocumentConverterSessionHistory>;
  singleFileHistory: ReturnType<typeof useDocumentConverterSessionHistory>;
}): void {
  const { project, projectHistory, singleFile, singleFileHistory, workspaceMode } = args;

  watch(
    () => project.latestOutcome.value?.entryId,
    (entryId) => {
      if (!entryId || !project.latestOutcome.value) {
        return;
      }
      const outcome = project.latestOutcome.value;
      if (outcome.type === "ready") {
        const cachedPreviews = new Map<
          string,
          {
            blob: Blob;
            contentType: string | null;
            filename: string | null;
          }
        >();
        cachedPreviews.set(outcome.artifact.artifact_id, {
          blob: outcome.previewBlob,
          contentType: outcome.previewContentType,
          filename: outcome.filename,
        });
        projectHistory.upsertEntry(
          {
            id: outcome.entryId,
            filename: outcome.filename,
            artifacts: outcome.preview.artifacts.map((artifact) => ({
              id: artifact.artifact_id,
              filename: artifact.filename,
              loadPreview: async () => {
                const cachedPreview = cachedPreviews.get(artifact.artifact_id);
                if (cachedPreview) {
                  cachedPreviews.delete(artifact.artifact_id);
                  return cachedPreview;
                }
                return await loadDocumentConverterProjectPreviewArtifactBlob({
                  previewId: outcome.preview.preview_id,
                  artifact,
                });
              },
              download: async (filenameStem?: string | null) => {
                const response = await downloadDocumentConverterProjectPreviewArtifact({
                  previewId: outcome.preview.preview_id,
                  artifact,
                  filenameStem,
                });
                triggerBrowserDownload(response.blob, response.filename ?? artifact.filename);
              },
              save: async (filenameStem?: string | null) => {
                await saveDocumentConverterProjectPreviewArtifact({
                  previewId: outcome.preview.preview_id,
                  artifact,
                  filenameStem,
                });
                await singleFile.loadSources();
              },
            })),
            resultTypeLabel: "PDF",
            sourceLabel: "HTML/CSS-projekt",
            status: "ready",
            retry: async () => {
              workspaceMode.value = "project_preview";
              await project.retryRequest(outcome.request);
            },
          },
          { select: true },
        );
        return;
      }

      projectHistory.upsertEntry(
        {
          id: outcome.entryId,
          filename: outcome.filename,
          resultTypeLabel: "PDF",
          sourceLabel: "HTML/CSS-projekt",
          status: "failed",
          errorMessage: outcome.errorMessage,
          retry: async () => {
            workspaceMode.value = "project_preview";
            await project.retryRequest(outcome.request);
          },
        },
        { select: false },
      );
    },
  );

  watch(
    () => singleFile.latestOutcome.value?.entryId,
    (entryId) => {
      if (!entryId || !singleFile.latestOutcome.value) {
        return;
      }
      const outcome = singleFile.latestOutcome.value;
      if (outcome.type === "ready") {
        singleFileHistory.upsertEntry(
          {
            id: outcome.entryId,
            filename: outcome.filename,
            artifacts: outcome.artifacts.map((artifact) => ({
              id: artifact.jobId,
              filename: artifact.filename,
              loadPreview: artifact.previewable
                ? async () => await downloadDocumentConverterJobArtifact({ jobId: artifact.jobId })
                : async () => null,
              download: async (filenameStem?: string | null) => {
                const response = await downloadDocumentConverterJobArtifact({
                  filenameStem,
                  jobId: artifact.jobId,
                });
                triggerBrowserDownload(response.blob, response.filename ?? artifact.filename);
              },
              save: async (filenameStem?: string | null) => {
                await saveDocumentConverterJobArtifact({ filenameStem, jobId: artifact.jobId });
                await singleFile.loadSources();
              },
            })),
            resultTypeLabel: outcome.resultTypeLabel,
            sourceLabel: outcome.sourceLabel,
            status: "ready",
            retry: async () => {
              workspaceMode.value = "single_file";
              await singleFile.retryRequest(outcome.request);
            },
          },
          { select: true },
        );
        return;
      }

      singleFileHistory.upsertEntry(
        {
          id: outcome.entryId,
          filename: outcome.filename,
          resultTypeLabel: outcome.resultTypeLabel,
          sourceLabel: outcome.sourceLabel,
          status: "failed",
          errorMessage: outcome.errorMessage,
          retry: async () => {
            workspaceMode.value = "single_file";
            await singleFile.retryRequest(outcome.request);
          },
        },
        { select: false },
      );
    },
  );
}
