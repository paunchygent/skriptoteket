<script setup lang="ts">
/**
 * Public Exam Converter job panel.
 *
 * Domain purpose:
 *   Render anonymous job state, structured errors, artifact availability, and
 *   named downloads without owning API polling or browser download mechanics.
 *
 * Relationships:
 *   - Receives state from `usePublicExamConverterRuntime`.
 *   - Emits refresh and download commands back to the runtime composable.
 */

import { AlertCircle, Download, RefreshCw } from "lucide-vue-next";

import UiDenseActionButton from "../../../components/ui/UiDenseActionButton.vue";
import UiDenseIconButton from "../../../components/ui/UiDenseIconButton.vue";
import type {
  ArtifactEntry,
  ArtifactManifest,
  StatusResponse,
  SubmitResponse,
} from "./examConverterPublicApi";

const props = defineProps<{
  currentJob: SubmitResponse | null;
  status: StatusResponse | null;
  manifest: ArtifactManifest | null;
  isPolling: boolean;
  errorMessage: string | null;
  downloadingArtifactKey: string | null;
  availableArtifactCount: number;
}>();

const emit = defineEmits<{
  refresh: [];
  download: [artifact: ArtifactEntry];
}>();

function availabilityLabel(value: string): string {
  switch (value) {
    case "available":
      return "Klar att hämta";
    case "blocked":
      return "Behöver kontrolleras";
    case "failed":
      return "Kunde inte skapas";
    case "not_requested":
      return "Inte vald";
    case "not_implemented":
      return "Inte tillgänglig ännu";
    case "not_supported_by_examnet":
      return "Stöds inte av Exam.net";
    default:
      return "Status okänd";
  }
}
</script>

<template>
  <section
    class="border border-navy bg-panel p-4 shadow-brutal-sm"
    aria-live="polite"
  >
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0">
        <p class="mb-1 text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          Jobb
        </p>
        <h2 class="break-words text-lg font-semibold leading-tight text-navy">
          {{ props.currentJob?.public_job_id ?? "Ingen körning" }}
        </h2>
      </div>
      <UiDenseIconButton
        label="Uppdatera status"
        :disabled="!props.currentJob || props.isPolling"
        @click="emit('refresh')"
      >
        <RefreshCw class="h-[18px] w-[18px]" />
      </UiDenseIconButton>
    </div>

    <p
      v-if="props.errorMessage"
      class="mt-4 flex items-center gap-2 border border-error/40 bg-error/10 px-3 py-2 text-sm font-semibold text-error"
    >
      <AlertCircle
        class="h-[18px] w-[18px] shrink-0"
        aria-hidden="true"
      />
      <span>{{ props.errorMessage }}</span>
    </p>

    <ul
      v-if="props.manifest"
      class="mt-4 grid gap-2"
    >
      <li
        v-for="artifact in props.manifest.artifacts"
        :key="artifact.artifact_key"
        class="flex min-h-14 items-center justify-between gap-3 border border-navy/20 bg-canvas/45 px-3 py-2"
      >
        <span class="min-w-0">
          <strong class="block break-words text-sm text-navy">
            {{ artifact.filename ?? artifact.artifact_key }}
          </strong>
          <small class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            {{ availabilityLabel(artifact.availability) }}
          </small>
        </span>
        <UiDenseActionButton
          v-if="artifact.download_url"
          class="exam-converter__download h-9 px-3 text-xs"
          label="Hämta"
          :busy="props.downloadingArtifactKey === artifact.artifact_key"
          busy-label="Hämtar"
          :disabled="props.downloadingArtifactKey === artifact.artifact_key"
          @click="emit('download', artifact)"
        >
          <template #leading>
            <Download class="h-[18px] w-[18px]" />
          </template>
        </UiDenseActionButton>
      </li>
    </ul>

    <p
      v-else
      class="mt-6 text-sm text-navy/65"
    >
      {{ props.currentJob ? "Väntar på färdiga filer." : "Redo för en engångskonvertering." }}
    </p>

    <p
      v-if="props.availableArtifactCount > 0"
      class="mt-4 text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60"
    >
      {{ props.availableArtifactCount }} fil(er) redo att hämta.
    </p>

    <p
      v-if="props.status?.error"
      class="mt-3 text-xs font-semibold text-error"
    >
      Konverteringen stannade. Kontrollera filen och försök igen.
    </p>
  </section>
</template>
