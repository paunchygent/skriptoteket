<script setup lang="ts">
/**
 * Public Exam Converter runtime view.
 *
 * Domain purpose:
 *   Compose the anonymous Exam Converter public route from focused upload and
 *   job panels while keeping grants, leases, polling, and download authority
 *   behind Skriptoteket public backend routes.
 *
 * Relationships:
 *   - Mounted by `curatedAppHostRegistry` for the scoped public app host route.
 *   - Delegates runtime state to `usePublicExamConverterRuntime`.
 */

import { AlertCircle, CheckCircle2, LoaderCircle } from "lucide-vue-next";

import PublicExamConverterJobPanel from "./exam-converter-public/PublicExamConverterJobPanel.vue";
import ExamConverterUploadPanel from "./exam-converter/ExamConverterUploadPanel.vue";
import { usePublicExamConverterRuntime } from "./exam-converter-public/usePublicExamConverterRuntime";

const {
  availableArtifacts,
  canSubmit,
  currentJob,
  downloadingArtifactKey,
  downloadArtifact,
  errorMessage,
  gradedResultPdfFileName,
  isPolling,
  isSubmitting,
  manifest,
  refreshJob,
  selectedTargets,
  setGradedResultPdfFile,
  setSourceDxeFile,
  sourceDxeFileName,
  status,
  statusLabel,
  submitJob,
  toggleTarget,
} = usePublicExamConverterRuntime();
</script>

<template>
  <main class="min-h-[calc(100vh-72px)] bg-canvas px-5 py-6 text-navy md:px-8">
    <header class="mx-auto mb-5 flex max-w-6xl flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        <p class="mb-1 text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          Provhantering
        </p>
        <h1 class="text-3xl font-semibold leading-tight text-navy">Exam Converter</h1>
      </div>
      <div
        class="inline-flex h-10 items-center gap-2 border px-3 text-sm font-semibold"
        :class="
          status?.status === 'succeeded'
            ? 'border-success/45 bg-success/10 text-success'
            : errorMessage
              ? 'border-error/40 bg-error/10 text-error'
              : 'border-navy/25 bg-panel text-navy'
        "
        :data-state="status?.status ?? 'idle'"
      >
        <CheckCircle2
          v-if="status?.status === 'succeeded'"
          class="h-[18px] w-[18px]"
          aria-hidden="true"
        />
        <LoaderCircle
          v-else-if="isSubmitting || isPolling || status?.status === 'processing'"
          class="h-[18px] w-[18px] animate-spin"
          aria-hidden="true"
        />
        <AlertCircle
          v-else-if="errorMessage"
          class="h-[18px] w-[18px]"
          aria-hidden="true"
        />
        <span>{{ statusLabel }}</span>
      </div>
    </header>

    <section
      class="mx-auto grid max-w-6xl gap-4 lg:grid-cols-[minmax(18rem,24rem)_minmax(0,1fr)]"
      aria-label="Exam Converter"
    >
      <ExamConverterUploadPanel
        :source-dxe-file-name="sourceDxeFileName"
        :graded-result-pdf-file-name="gradedResultPdfFileName"
        :selected-targets="selectedTargets"
        :can-submit="canSubmit"
        :is-submitting="isSubmitting"
        @source-file-change="setSourceDxeFile"
        @graded-result-file-change="setGradedResultPdfFile"
        @target-change="toggleTarget"
        @submit="submitJob"
      />

      <PublicExamConverterJobPanel
        :current-job="currentJob"
        :status="status"
        :manifest="manifest"
        :is-polling="isPolling"
        :error-message="errorMessage"
        :downloading-artifact-key="downloadingArtifactKey"
        :available-artifact-count="availableArtifacts.length"
        @refresh="refreshJob"
        @download="downloadArtifact"
      />
    </section>
  </main>
</template>
