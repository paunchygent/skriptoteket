<script setup lang="ts">
/**
 * Exam Converter workflow rail shell.
 *
 * Domain purpose:
 *   Reserve the stable left-side Exam Converter setup rail for source-file
 *   state, optional supporting file state, target-file declarations, and later
 *   conversion actions without becoming the primary work surface.
 *
 * Relationships:
 *   - Rendered by `ExamConverterAuthenticatedView`.
 *   - Receives browser-local source-file state from the authenticated host.
 */

import { Check, FileText, HelpCircle, Play, Upload, X } from "lucide-vue-next";

import type { ExamConverterSourceFileSelection } from "./useExamConverterSourceFile";

defineProps<{
  selectedSourceFile: ExamConverterSourceFileSelection | null;
}>();

const emit = defineEmits<{
  clearSourceFile: [];
}>();
</script>

<template>
  <aside
    class="bg-panel p-4 border-r border-navy/20"
    aria-labelledby="exam-converter-workflow-title"
    data-test="exam-converter-workflow-rail-shell"
  >
    <div>
      <h1
        id="exam-converter-workflow-title"
        class="text-base font-semibold leading-tight text-navy"
      >
        Konvertera prov
      </h1>
    </div>

    <div class="mt-5 grid gap-6">
      <section
        class="grid gap-2"
        data-test="exam-converter-source-file-state"
      >
        <h2 class="text-sm font-semibold leading-tight text-navy">
          1. Provfil
        </h2>
        <div
          v-if="selectedSourceFile"
          class="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 border border-navy/25 bg-panel px-3 py-3"
          data-test="exam-converter-selected-source-file"
        >
          <FileText
            class="h-5 w-5 text-navy"
            aria-hidden="true"
          />
          <span class="min-w-0">
            <span class="block truncate text-sm font-medium leading-snug text-navy">
              {{ selectedSourceFile.name }}
            </span>
            <span class="mt-0.5 block text-xs leading-none text-navy/65">
              {{ selectedSourceFile.sizeLabel }}
            </span>
          </span>
          <button
            type="button"
            class="grid h-7 w-7 place-items-center border border-navy/25 bg-panel-muted text-navy hover:bg-canvas"
            aria-label="Ta bort provfil"
            data-test="exam-converter-clear-source-file"
            @click="emit('clearSourceFile')"
          >
            <X
              class="h-4 w-4"
              aria-hidden="true"
            />
          </button>
        </div>
        <div
          v-else
          class="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-3 border border-navy/25 bg-panel px-3 py-3"
        >
          <Upload
            class="h-5 w-5 text-action"
            aria-hidden="true"
          />
          <span class="min-w-0 text-sm font-medium leading-snug text-navy">
            Välj provfil (.dxe)
          </span>
        </div>
        <p
          v-if="!selectedSourceFile"
          class="text-xs leading-snug text-navy/65"
        >
          Ingen fil vald.
        </p>
        <p
          v-else
          class="flex items-center gap-2 text-xs leading-snug text-success"
        >
          <Check
            class="h-3 w-3"
            aria-hidden="true"
          />
          Filen är uppladdad
        </p>
      </section>

      <section
        class="grid gap-2"
        data-test="exam-converter-supporting-file-state"
      >
        <h2 class="text-sm font-semibold leading-tight text-navy">
          2. Valfri resultat-PDF
        </h2>
        <div class="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-3 border border-navy/25 bg-panel px-3 py-3">
          <FileText
            class="h-5 w-5 text-navy"
            aria-hidden="true"
          />
          <span class="min-w-0 text-sm font-medium leading-snug text-navy">
            Välj fil
          </span>
        </div>
        <p class="text-xs leading-snug text-navy/65">
          För svarsmall.
        </p>
      </section>

      <section
        class="grid gap-2"
        data-test="exam-converter-target-file-state"
      >
        <h2 class="text-sm font-semibold leading-tight text-navy">
          3. Målfiler
        </h2>
        <div class="grid gap-2">
          <div class="border border-navy/25 bg-panel px-3 py-3">
            <div class="flex items-center gap-2 text-sm font-medium leading-snug text-navy">
              <span class="grid h-5 w-5 place-items-center border border-navy bg-navy text-button-primary-text">
                <Check
                  class="h-3 w-3"
                  aria-hidden="true"
                />
              </span>
              PDF
              <HelpCircle
                class="ml-auto h-4 w-4 text-action"
                aria-hidden="true"
              />
            </div>
            <p class="mt-2 text-xs leading-snug text-navy/65">
              För direktimport av prov i Exam.net.
            </p>
          </div>

          <div class="border border-navy/25 bg-panel px-3 py-3">
            <div class="flex items-center gap-2 text-sm font-medium leading-snug text-navy">
              <span class="grid h-5 w-5 place-items-center border border-navy bg-navy text-button-primary-text">
                <Check
                  class="h-3 w-3"
                  aria-hidden="true"
                />
              </span>
              QTI-format
              <HelpCircle
                class="ml-auto h-4 w-4 text-action"
                aria-hidden="true"
              />
            </div>
            <p class="mt-2 text-xs leading-snug text-navy/65">
              För lagring och import. Exam.net-stöd är planerat.
            </p>
          </div>
        </div>
      </section>

      <section class="grid gap-3">
        <h2 class="text-sm font-semibold leading-tight text-navy">
          4. Konvertera
        </h2>
        <button
          type="button"
          class="btn-cta justify-center gap-2 shadow-none"
          disabled
        >
          <Play
            class="h-4 w-4"
            aria-hidden="true"
          />
          Starta konvertering
        </button>
        <button
          type="button"
          class="btn-ghost justify-center shadow-none"
          disabled
        >
          Rensa val
        </button>
      </section>
    </div>
  </aside>
</template>
