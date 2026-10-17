<script setup lang="ts">
/**
 * Centered tutorial clip dialog for Klassrumskartan.
 *
 * Purpose:
 *   Show one section's clips: a 16:9 player with poster and play control, and
 *   the section's other clips beneath. The video loads nothing until the user
 *   presses play and never starts on its own.
 *
 * Relationships:
 *   - opened by `TutorialFirstUseGate.vue` (first use) and
 *     `TutorialClipThumbnails.vue` (Hjälp)
 *   - overlay structure follows `PlannerConfirmationDialog.vue`; teleported to
 *     body so it sits above the Hjälp panel
 */

import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

import UiDenseIconButton from "../../ui/shared/components/UiDenseIconButton.vue";
import SystemMessage from "../../ui/shared/components/SystemMessage.vue";
import IconRun from "../../icons/IconRun.vue";
import IconX from "../../icons/IconX.vue";
import { resolveTutorialMediaUrl, type TutorialClip } from "../../../api/tutorialClips";
import { formatClipDuration, TUTORIAL_COPY } from "./tutorialCopy";

const props = defineProps<{
  clips: TutorialClip[];
  initialClipId?: string | null;
  open: boolean;
}>();

const emit = defineEmits<{
  (e: "close"): void;
}>();

const titleId = `tutorial-clip-title-${Math.random().toString(36).slice(2, 10)}`;

const currentClipId = ref<string | null>(null);
const hasStarted = ref(false);
const hasLoadError = ref(false);
const overlayRef = ref<HTMLElement | null>(null);
const panelRef = ref<HTMLElement | null>(null);
const playButtonRef = ref<HTMLButtonElement | null>(null);
const videoRef = ref<HTMLVideoElement | null>(null);
let restoreFocusTarget: HTMLElement | null = null;

const currentClip = computed<TutorialClip | null>(() => {
  return (
    props.clips.find((clip) => clip.id === currentClipId.value) ?? props.clips[0] ?? null
  );
});
const otherClips = computed(() => props.clips.length > 1 ? props.clips : []);

function selectClip(clipId: string): void {
  currentClipId.value = clipId;
  hasStarted.value = false;
  hasLoadError.value = false;
}

function play(): void {
  const video = videoRef.value;
  if (!video) {
    return;
  }
  hasStarted.value = true;
  // The play control unmounts once playback starts; move focus to the video so
  // keyboard control and the focus ring stay inside the dialog.
  video.focus({ preventScroll: true });
  const result = video.play() as Promise<void> | undefined;
  result?.catch(() => undefined);
}

function onVideoError(): void {
  hasLoadError.value = true;
  hasStarted.value = false;
}

function close(): void {
  emit("close");
}

function focusableElements(): HTMLElement[] {
  const panel = panelRef.value;
  if (!panel) {
    return [];
  }
  return Array.from(
    panel.querySelectorAll<HTMLElement>(
      "button:not([disabled]), video[controls], [href], [tabindex]:not([tabindex='-1'])",
    ),
  );
}

function handleDocumentKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    // Capture phase: the Hjälp panel's own Escape handler must not also fire.
    event.stopPropagation();
    event.preventDefault();
    close();
    return;
  }
  if (event.key !== "Tab") {
    return;
  }
  // Inside the panel the browser moves focus itself, so a video's native
  // controls stay reachable; the edge sentinels wrap it. Only focus that has
  // left the dialog is pulled back here.
  const active = document.activeElement;
  if (active instanceof Node && overlayRef.value?.contains(active)) {
    return;
  }
  event.preventDefault();
  if (event.shiftKey) {
    focusLast();
  } else {
    focusFirst();
  }
}

function focusFirst(): void {
  focusableElements()[0]?.focus();
}

function focusLast(): void {
  focusableElements().at(-1)?.focus();
}

function activate(): void {
  restoreFocusTarget =
    document.activeElement instanceof HTMLElement ? document.activeElement : null;
  selectClip(props.initialClipId ?? props.clips[0]?.id ?? "");
  document.addEventListener("keydown", handleDocumentKeydown, true);
  void nextTick(() => {
    (playButtonRef.value ?? panelRef.value)?.focus({ preventScroll: true });
  });
}

function deactivate(): void {
  document.removeEventListener("keydown", handleDocumentKeydown, true);
  const target = restoreFocusTarget;
  restoreFocusTarget = null;
  if (target && document.contains(target)) {
    target.focus({ preventScroll: true });
  }
}

watch(
  () => props.open,
  (isOpen, wasOpen) => {
    if (isOpen) {
      activate();
    } else if (wasOpen) {
      deactivate();
    }
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  if (props.open) {
    deactivate();
  }
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open && currentClip"
      ref="overlayRef"
      class="fixed inset-0 z-50 overflow-y-auto p-4"
      data-test="tutorial-clip-dialog"
    >
      <button
        type="button"
        :aria-label="TUTORIAL_COPY.close"
        tabindex="-1"
        class="planner-overlay-backdrop"
        data-test="tutorial-clip-dialog-backdrop"
        @click="close"
      />
      <span
        tabindex="0"
        class="sr-only"
        data-test="tutorial-clip-focus-start"
        @focus="focusLast"
      />
      <div class="relative flex min-h-full items-center justify-center py-4">
        <section
          ref="panelRef"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          tabindex="-1"
          class="tutorial-clip-dialog-panel w-full max-w-[60rem] border border-[var(--huleedu-panel-border)] bg-modal shadow-md"
        >
          <header class="flex items-center justify-between gap-3 border-b border-navy/20 px-5 py-3">
            <h2
              :id="titleId"
              class="min-w-0 truncate text-lg font-semibold text-navy"
              :title="currentClip.title"
              data-test="tutorial-clip-dialog-title"
            >
              {{ currentClip.title }}
            </h2>
            <UiDenseIconButton
              size="touch"
              :label="TUTORIAL_COPY.close"
              :title="TUTORIAL_COPY.close"
              data-test="tutorial-clip-dialog-close"
              @click="close"
            >
              <IconX :size="20" />
            </UiDenseIconButton>
          </header>

          <div class="relative aspect-video w-full bg-navy">
            <video
              :key="currentClip.id"
              ref="videoRef"
              class="absolute inset-0 h-full w-full"
              controls
              tabindex="0"
              playsinline
              preload="none"
              :poster="resolveTutorialMediaUrl(currentClip.poster)"
              :src="resolveTutorialMediaUrl(currentClip.video)"
              data-test="tutorial-clip-video"
              @play="hasStarted = true"
              @error="onVideoError"
            />
            <button
              v-if="!hasStarted && !hasLoadError"
              ref="playButtonRef"
              type="button"
              class="tutorial-clip-play"
              :aria-label="`${TUTORIAL_COPY.play}: ${currentClip.title}`"
              :title="TUTORIAL_COPY.play"
              data-test="tutorial-clip-play"
              @click="play"
            >
              <span class="tutorial-clip-play-disc">
                <IconRun :size="36" />
              </span>
            </button>
            <div
              v-if="hasLoadError"
              class="absolute inset-x-0 bottom-0"
            >
              <SystemMessage
                tone="failure"
                data-test="tutorial-clip-error"
              >
                {{ TUTORIAL_COPY.loadError }}
              </SystemMessage>
            </div>
          </div>

          <ul
            v-if="otherClips.length > 0"
            class="divide-y divide-navy/15 border-b border-navy/20"
            :aria-label="TUTORIAL_COPY.moreClips"
          >
            <li
              v-for="clip in otherClips"
              :key="clip.id"
            >
              <button
                type="button"
                class="tutorial-clip-list-item"
                :aria-current="clip.id === currentClip.id ? 'true' : undefined"
                data-test="tutorial-clip-list-item"
                @click="selectClip(clip.id)"
              >
                <span class="min-w-0 truncate">{{ clip.title }}</span>
                <span class="shrink-0 font-mono text-xs text-navy/60">
                  {{ formatClipDuration(clip.duration_seconds) }}
                </span>
              </button>
            </li>
          </ul>

          <p class="px-5 py-3 text-sm text-navy/60">
            {{ TUTORIAL_COPY.findAgain }}
          </p>
        </section>
      </div>
      <span
        tabindex="0"
        class="sr-only"
        data-test="tutorial-clip-focus-end"
        @focus="focusFirst"
      />
    </div>
  </Teleport>
</template>

<style scoped>
.tutorial-clip-dialog-panel:focus {
  outline: none;
}

.tutorial-clip-play {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--huleedu-navy);
}

.tutorial-clip-play-disc {
  display: flex;
  height: 5rem;
  width: 5rem;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--huleedu-navy);
  border-radius: 9999px;
  background: var(--huleedu-canvas);
  transition: background-color var(--huleedu-duration-fast) var(--huleedu-ease-default),
    color var(--huleedu-duration-fast) var(--huleedu-ease-default);
}

.tutorial-clip-list-item {
  display: flex;
  width: 100%;
  min-height: 2.75rem;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.5rem 1.25rem;
  text-align: left;
  font-size: var(--huleedu-text-sm);
  color: var(--huleedu-navy);
  transition: background-color var(--huleedu-duration-fast) var(--huleedu-ease-default);
}

.tutorial-clip-list-item[aria-current="true"] {
  font-weight: var(--huleedu-font-semibold);
  background: var(--huleedu-canvas);
}

.tutorial-clip-play:focus-visible .tutorial-clip-play-disc,
.tutorial-clip-list-item:focus-visible {
  outline: 2px solid var(--huleedu-action-40);
  outline-offset: 2px;
}

@media (hover: hover) and (pointer: fine) {
  .tutorial-clip-play:hover .tutorial-clip-play-disc {
    background: var(--huleedu-navy);
    color: var(--huleedu-canvas);
  }

  .tutorial-clip-list-item:hover {
    background: var(--huleedu-canvas);
  }
}
</style>
