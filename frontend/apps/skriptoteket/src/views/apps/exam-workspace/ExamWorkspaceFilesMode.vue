<script setup lang="ts">
/**
 * Exam workspace Filer mode.
 *
 * Domain purpose:
 *   Everything about the exam as a file: import a .docx exam, open a saved
 *   exam, see whether the open exam is ready for Exam.net, create QTI, PDF,
 *   and DOCX files, ask for answer-key proposals, and reload the saved
 *   version. Questions that stop an export link straight to Redigera.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` as the Filer mode pane; the view owns
 *     state and file validation and handles every emitted intent.
 *   - Composes `ExamWorkspaceSavedDocuments`, `ExamWorkspaceExportPanel`,
 *     and `ExamWorkspaceEnrichmentPanel`.
 */

import { IconCheck, IconWarning } from "../../../components/icons";
import { Upload } from "lucide-vue-next";

import type {
  ExamWorkspaceDocumentSummary,
  ExamWorkspaceExportTarget,
} from "../../../api/examWorkspace";
import ExamWorkspaceEnrichmentPanel from "./ExamWorkspaceEnrichmentPanel.vue";
import ExamWorkspaceExportPanel from "./ExamWorkspaceExportPanel.vue";
import ExamWorkspaceSavedDocuments from "./ExamWorkspaceSavedDocuments.vue";

export type ExamWorkspaceReadinessEntry = {
  itemId: string;
  sequence: number;
  title: string;
  reasons: string[];
};

defineProps<{
  compact: boolean;
  enrichmentDisabled: boolean;
  enrichmentMessage: string | null;
  exportNotice: string | null;
  exportingTarget: ExamWorkspaceExportTarget | null;
  hasDocument: boolean;
  isBusy: boolean;
  isDirty: boolean;
  notes: string[];
  readiness: ExamWorkspaceReadinessEntry[];
  savedDocuments: ExamWorkspaceDocumentSummary[];
  sourceFileError: string | null;
}>();

const emit = defineEmits<{
  dropFiles: [files: File[]];
  export: [target: ExamWorkspaceExportTarget];
  goToItem: [itemId: string];
  open: [lineageId: string];
  reload: [];
  requestProposals: [];
  selectFile: [file: File];
}>();

function handleSourceFileInput(event: Event): void {
  const input = event.target as HTMLInputElement;
  const [file] = Array.from(input.files ?? []);
  if (file) {
    emit("selectFile", file);
  }
  input.value = "";
}

function handleDrop(event: DragEvent): void {
  emit("dropFiles", Array.from(event.dataTransfer?.files ?? []));
}
</script>

<template>
  <div
    class="grid content-start gap-6 p-4"
    :class="compact ? 'grid-cols-1' : 'grid-cols-[minmax(16rem,22rem)_minmax(0,1fr)] gap-x-8 p-6'"
  >
    <div
      class="grid content-start gap-6"
      data-test="exam-workspace-files-source"
    >
      <section class="grid gap-2">
        <h2 class="text-sm font-semibold leading-tight text-navy">
          {{ hasDocument ? 'Importera ett annat prov' : 'Provfil' }}
        </h2>
        <label
          class="grid cursor-pointer gap-2 border border-dashed border-navy/35 bg-canvas px-3 py-5 text-center hover:bg-panel"
          :class="isBusy ? 'cursor-not-allowed opacity-60' : undefined"
          data-test="exam-workspace-drop-zone"
          @dragover.prevent
          @drop.prevent="handleDrop"
        >
          <input
            class="sr-only"
            type="file"
            accept=".docx"
            :disabled="isBusy"
            data-test="exam-workspace-source-file-input"
            @change="handleSourceFileInput"
          >
          <Upload
            class="mx-auto h-5 w-5 text-action"
            aria-hidden="true"
          />
          <span class="text-sm font-medium leading-snug text-navy">
            Välj provfil (.docx)
          </span>
          <span class="text-xs leading-snug text-navy/65">
            Dra hit .docx-filen eller välj provfilen här.
          </span>
        </label>
        <p
          v-if="sourceFileError"
          class="text-xs leading-snug text-error"
          data-test="exam-workspace-source-file-error"
        >
          {{ sourceFileError }}
        </p>
        <p
          v-else-if="hasDocument && isDirty"
          class="text-xs leading-snug text-navy/65"
        >
          Spara det öppna provet innan du importerar ett annat.
        </p>
      </section>

      <ExamWorkspaceSavedDocuments
        :documents="savedDocuments"
        :is-busy="isBusy"
        :is-dirty="isDirty"
        @open="emit('open', $event)"
      />
    </div>

    <div class="grid content-start gap-6">
      <template v-if="hasDocument">
        <section
          class="grid gap-2"
          aria-labelledby="exam-workspace-readiness-title"
          data-test="exam-workspace-readiness"
        >
          <h2
            id="exam-workspace-readiness-title"
            class="text-sm font-semibold leading-tight text-navy"
          >
            Redo för Exam.net
          </h2>
          <p
            v-if="readiness.length === 0"
            class="inline-flex items-center gap-2 text-sm leading-snug text-navy"
            data-test="exam-workspace-readiness-ok"
          >
            <IconCheck
              :size="18"
              class="h-[1.125rem] w-[1.125rem] shrink-0 text-success"
              aria-hidden="true"
            />
            Alla frågor är klara för export.
          </p>
          <template v-else>
            <p class="inline-flex items-center gap-2 text-sm leading-snug text-navy">
              <IconWarning
                :size="18"
                class="h-[1.125rem] w-[1.125rem] shrink-0 text-warning"
                aria-hidden="true"
              />
              {{ readiness.length === 1 ? '1 fråga behöver åtgärdas' : `${readiness.length} frågor behöver åtgärdas` }} innan filerna kan skapas.
            </p>
            <ul class="grid gap-1">
              <li
                v-for="entry in readiness"
                :key="entry.itemId"
              >
                <button
                  type="button"
                  class="grid w-full gap-0.5 border border-navy/20 bg-canvas px-3 py-2 text-left hover:bg-panel"
                  :data-test="`exam-workspace-readiness-item-${entry.itemId}`"
                  @click="emit('goToItem', entry.itemId)"
                >
                  <span class="truncate text-sm font-medium leading-snug text-navy">
                    Fråga {{ entry.sequence }}<template v-if="entry.title"> – {{ entry.title }}</template>
                  </span>
                  <span class="text-xs leading-snug text-navy/70">
                    {{ entry.reasons.join(' ') }}
                  </span>
                </button>
              </li>
            </ul>
          </template>
        </section>

        <ExamWorkspaceExportPanel
          :export-notice="exportNotice"
          :exporting-target="exportingTarget"
          :is-busy="isBusy"
          :is-dirty="isDirty"
          @export="emit('export', $event)"
        />

        <ExamWorkspaceEnrichmentPanel
          :disabled="enrichmentDisabled"
          :message="enrichmentMessage"
          @request="emit('requestProposals')"
        />

        <section
          v-if="notes.length > 0"
          class="grid gap-2"
        >
          <h2 class="text-sm font-semibold leading-tight text-navy">
            Anteckningar från importen
          </h2>
          <ul
            class="grid gap-1 text-xs leading-snug text-navy/70"
            data-test="exam-workspace-notes"
          >
            <li
              v-for="note in notes"
              :key="note"
            >
              {{ note }}
            </li>
          </ul>
        </section>

        <section class="grid gap-2">
          <h2 class="text-sm font-semibold leading-tight text-navy">
            Sparad version
          </h2>
          <button
            type="button"
            class="btn-ghost justify-self-start shadow-none"
            :disabled="isBusy"
            data-test="exam-workspace-reload"
            @click="emit('reload')"
          >
            Läs in på nytt
          </button>
          <p class="text-xs leading-snug text-navy/65">
            Hämtar den senast sparade versionen och tar bort osparade ändringar.
          </p>
        </section>
      </template>

      <section
        v-else
        class="grid min-h-[12rem] place-items-center border border-dashed border-navy/20 p-8 text-center"
        data-test="exam-workspace-empty"
      >
        <div class="grid gap-2">
          <h2 class="text-sm font-semibold leading-tight text-navy">
            Inget prov är inläst
          </h2>
          <p class="text-xs leading-snug text-navy/65">
            Ladda upp ett .docx-prov eller öppna ett sparat prov för att börja.
          </p>
        </div>
      </section>
    </div>
  </div>
</template>
