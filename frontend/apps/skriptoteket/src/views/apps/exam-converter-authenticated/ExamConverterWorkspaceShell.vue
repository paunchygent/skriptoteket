<script setup lang="ts">
/**
 * Exam Converter workspace shell.
 *
 * Domain purpose:
 *   Reserve the dominant right-side workspace for approved Exam Converter
 *   intake, result, inspection, and review slices while keeping the host frame
 *   free of transport or conversion behavior.
 *
 * Relationships:
 *   - Rendered by `ExamConverterAuthenticatedView`.
 *   - Owns the idle source-file drop zone before later slices replace it with
 *     result strip, inspection modes, and focused review surfaces.
 */

import { Upload } from "lucide-vue-next";
</script>

<template>
  <section
    class="flex h-full min-h-[26rem] flex-col bg-panel"
    aria-labelledby="exam-converter-auth-title"
    data-test="exam-converter-workspace-shell"
  >
    <header class="px-4 py-4">
      <div class="min-w-0">
        <h2
          id="exam-converter-auth-title"
          class="text-lg font-semibold leading-tight text-navy"
        >
          Välj provfil för att börja
        </h2>
        <p class="mt-1 text-sm leading-snug text-navy/70">
          Dra hit .dxe-filen eller välj fil från datorn.
        </p>
      </div>
    </header>

    <div class="flex min-h-0 flex-1 px-4 pb-4">
      <div
        class="grid min-h-0 w-full flex-1 border border-dashed border-navy/45 bg-canvas px-6 py-6"
        data-test="exam-converter-source-drop-zone"
      >
        <div class="flex h-full min-w-0 items-center justify-center gap-4">
          <span
            class="grid h-12 w-12 shrink-0 place-items-center border border-navy/25 bg-panel"
            aria-hidden="true"
          >
            <Upload class="h-6 w-6 text-action" />
          </span>
          <div class="min-w-0">
            <p class="text-base font-medium leading-tight text-navy">
              Välj provfil
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
