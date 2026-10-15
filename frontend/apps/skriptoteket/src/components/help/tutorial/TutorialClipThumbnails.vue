<script setup lang="ts">
/**
 * Tutorial clip thumbnails for one planner Hjälp section.
 *
 * Purpose:
 *   List the section's clips as poster thumbnails with title and duration;
 *   each opens the shared clip dialog on every screen width. Renders nothing
 *   when the manifest has no clips for the section.
 *
 * Relationships:
 *   - mounted by `topics/HelpTopicPlanner.vue`
 *   - opens `TutorialClipDialog.vue`; seen-state belongs to the first-use gate
 */

import { computed, ref } from "vue";

import { resolveTutorialMediaUrl } from "../../../api/tutorialClips";
import TutorialClipDialog from "./TutorialClipDialog.vue";
import { useTutorialClipManifest } from "./useTutorialClipManifest";
import { formatClipDuration, TUTORIAL_COPY } from "./tutorialCopy";

const props = defineProps<{ section: string }>();

const manifest = useTutorialClipManifest();
const clips = computed(() => manifest.clipsForSection(props.section));

const openClipId = ref<string | null>(null);
</script>

<template>
  <div
    v-if="clips.length > 0"
    data-test="tutorial-clip-thumbnails"
  >
    <ul
      class="grid grid-cols-2 gap-3"
      :aria-label="TUTORIAL_COPY.thumbnailsLabel"
    >
      <li
        v-for="clip in clips"
        :key="clip.id"
      >
        <button
          type="button"
          class="tutorial-clip-thumbnail"
          :aria-label="`${TUTORIAL_COPY.play}: ${clip.title}`"
          :title="clip.title"
          data-test="tutorial-clip-thumbnail"
          @click="openClipId = clip.id"
        >
          <span class="relative block aspect-video w-full overflow-hidden border border-navy/20 bg-navy/10">
            <img
              :src="resolveTutorialMediaUrl(clip.poster)"
              alt=""
              loading="lazy"
              decoding="async"
              class="absolute inset-0 h-full w-full object-cover"
            >
            <span class="absolute bottom-1 right-1 bg-navy px-1.5 py-0.5 font-mono text-[11px] text-canvas">
              {{ formatClipDuration(clip.duration_seconds) }}
            </span>
          </span>
          <span class="mt-1 block truncate text-left text-sm font-semibold text-navy">
            {{ clip.title }}
          </span>
        </button>
      </li>
    </ul>

    <TutorialClipDialog
      :clips="clips"
      :initial-clip-id="openClipId"
      :open="openClipId !== null"
      @close="openClipId = null"
    />
  </div>
</template>

<style scoped>
.tutorial-clip-thumbnail {
  display: block;
  width: 100%;
  transition: opacity var(--huleedu-duration-default) ease;
}

.tutorial-clip-thumbnail:focus-visible {
  outline: 2px solid var(--huleedu-action-40);
  outline-offset: 2px;
}

@media (hover: hover) and (pointer: fine) {
  .tutorial-clip-thumbnail:hover {
    opacity: 0.85;
  }
}
</style>
