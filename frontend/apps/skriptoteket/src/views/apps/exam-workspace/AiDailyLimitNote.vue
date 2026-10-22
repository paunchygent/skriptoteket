<script setup lang="ts">
/**
 * Exam workspace daily-limit note.
 *
 * Domain purpose:
 *   The one inline note every drawer AI control shows once the LLM door has
 *   refused an AI action for the day: the door's own sentence for the first
 *   refused limit. This is presentation only; the page-session flag lives in
 *   `aiDailyLimit`.
 *
 * Relationships:
 *   - Rendered by the export blockers, the details drawer and the import
 *     box next to their disabled AI control. The header toolbar and the
 *     Öppna drop zone keep their own wrappers for layout reasons and read
 *     the same note directly.
 */

import { aiDailyLimitFor } from "../../../composables/aiDailyLimit";

const { note: aiDailyLimitNote } = aiDailyLimitFor("small");

withDefaults(
  defineProps<{
    /** Test hook for the note; one stable hook keeps every control's proof alike. */
    testId?: string;
  }>(),
  { testId: "ai-daily-limit-note" },
);
</script>

<template>
  <p
    class="xw-hint"
    :data-test="testId"
  >
    {{ aiDailyLimitNote }}
  </p>
</template>
