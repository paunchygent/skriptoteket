<script setup lang="ts">
/**
 * First-use tutorial dialog host for Klassrumskartan.
 *
 * Mounted once per planner host by `ClassroomPlannerEntryView`; the rules live
 * in `useTutorialFirstUse.ts`.
 */

import TutorialClipDialog from "./TutorialClipDialog.vue";
import { useTutorialFirstUse } from "./useTutorialFirstUse";
import type { TutorialHostMode } from "./useTutorialSeenSections";

const props = defineProps<{
  hostMode: TutorialHostMode;
  blocked: boolean;
}>();

const firstUse = useTutorialFirstUse({
  hostMode: props.hostMode,
  blocked: () => props.blocked,
});
const openSection = firstUse.openSection;
const openClips = firstUse.openClips;
</script>

<template>
  <TutorialClipDialog
    :clips="openClips"
    :open="openSection !== null"
    @close="firstUse.close"
  />
</template>
