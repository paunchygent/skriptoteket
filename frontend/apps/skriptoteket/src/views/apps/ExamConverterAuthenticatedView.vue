<script setup lang="ts">
/**
 * Authenticated Exam Converter host frame.
 *
 * Domain purpose:
 *   Provide the stable signed-in Exam Converter workspace frame before
 *   workflow, result, file, question, report, or save behavior is introduced.
 *
 * Relationships:
 *   - Mounted by `curatedAppHostRegistry` for authenticated Conversion Hub.
 *   - Composes structural shell components only; transport/runtime state is
 *     introduced by later approved UI slices.
 */

import ExamConverterWorkflowRailShell from "./exam-converter-authenticated/ExamConverterWorkflowRailShell.vue";
import ExamConverterWorkspaceShell from "./exam-converter-authenticated/ExamConverterWorkspaceShell.vue";
</script>

<template>
  <main
    class="min-h-[calc(100vh-72px)] overflow-x-auto bg-canvas px-4 py-5 text-navy md:px-6 lg:px-8"
    aria-labelledby="exam-converter-auth-title"
  >
    <section
      class="mx-auto grid min-h-[28rem] min-w-[62rem] max-w-[90rem] grid-cols-[18rem_minmax(0,1fr)] items-stretch border border-navy bg-panel shadow-brutal-sm xl:grid-cols-[19rem_minmax(0,1fr)]"
      aria-label="Exam Converter"
      data-test="exam-converter-host-frame"
    >
      <ExamConverterWorkflowRailShell />
      <ExamConverterWorkspaceShell />
    </section>
  </main>
</template>
