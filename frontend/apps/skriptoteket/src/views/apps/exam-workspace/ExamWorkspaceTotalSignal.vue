<script setup lang="ts">
/** Live, advisory exam-total comparison; does not participate in export readiness. */
import { computed } from "vue";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { UiDenseStatusPill } from "../../../components/ui";
import { examWorkspaceExamTotalSignal } from "./examWorkspaceTotals";

const props = defineProps<{ document: NativeExamDocument }>();
const totalsSignal = computed(() => examWorkspaceExamTotalSignal(props.document));
</script>

<template>
  <UiDenseStatusPill
    v-if="totalsSignal"
    :label="totalsSignal"
    :title="totalsSignal"
    tone="warning"
    class="min-w-0 max-w-full overflow-hidden whitespace-nowrap"
    data-test="exam-workspace-total-signal"
  />
</template>
