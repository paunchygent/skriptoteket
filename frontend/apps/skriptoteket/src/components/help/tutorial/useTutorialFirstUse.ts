/**
 * First-use gate for the Klassrumskartan tutorial clip dialog.
 *
 * Purpose:
 *   Open a planner section's clip dialog once, the first time the teacher
 *   reaches that section at desktop width, and only when nothing else asks for
 *   the teacher's attention. Closing the dialog marks the section seen.
 *
 * Rules:
 *   - A planner help-context change (`planner_*`) makes that section pending.
 *   - The pending section waits for the start-up inputs: the clip manifest,
 *     the seen-state source and an unblocked guest-upgrade gate. Each time one
 *     of them changes, the 500 ms delay restarts.
 *   - After the delay the section opens only if it has clips, is unseen, the
 *     viewport is desktop, the Hjälp panel is closed and no other dialog is
 *     present. Otherwise it is dropped until the next context change; no timer
 *     retries it.
 *
 * Relationships:
 *   - used by `TutorialFirstUseGate.vue`, mounted by `ClassroomPlannerEntryView`
 *   - reads `useHelp().helpContext`, set by the planner workspace shells
 */

import { computed, onScopeDispose, ref, toValue, watch } from "vue";
import type { ComputedRef, MaybeRefOrGetter, Ref } from "vue";

import { useHelp } from "../useHelp";
import {
  isTutorialSection,
  type TutorialClip,
  type TutorialSection,
} from "../../../api/tutorialClips";
import { useDesktopViewport } from "./useDesktopViewport";
import { useTutorialClipManifest } from "./useTutorialClipManifest";
import { useTutorialSeenSections, type TutorialHostMode } from "./useTutorialSeenSections";

const TUTORIAL_FIRST_USE_DELAY_MS = 500;

/**
 * Dialogs that must not be covered. Any element with the dialog role counts,
 * modal or not, such as the nonmodal Delade länkar panel. The planner's own
 * overlay dialogs (confirmations, roster and room modals) use the shared
 * backdrop class without a dialog role, so that class counts as well. The
 * Hjälp panel is checked separately through `useHelp().isOpen`.
 */
const FOREIGN_DIALOG_SELECTOR = '[role="dialog"], .planner-overlay-backdrop';

function isForeignDialogPresent(root: ParentNode = document): boolean {
  return root.querySelector(FOREIGN_DIALOG_SELECTOR) !== null;
}

export type TutorialFirstUse = {
  openSection: Ref<TutorialSection | null>;
  openClips: ComputedRef<TutorialClip[]>;
  close: () => void;
};

export function useTutorialFirstUse(options: {
  hostMode: TutorialHostMode;
  blocked: MaybeRefOrGetter<boolean>;
}): TutorialFirstUse {
  const help = useHelp();
  const manifest = useTutorialClipManifest();
  const seen = useTutorialSeenSections(options.hostMode);
  const isDesktop = useDesktopViewport();

  const pendingSection = ref<TutorialSection | null>(null);
  const openSection = ref<TutorialSection | null>(null);
  let timer: ReturnType<typeof setTimeout> | null = null;

  const startupReady = computed(
    () => manifest.loaded.value && seen.ready.value && !toValue(options.blocked),
  );

  function clearTimer(): void {
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
  }

  function evaluate(): void {
    timer = null;
    const section = pendingSection.value;
    if (!section || openSection.value || !startupReady.value) {
      return;
    }
    pendingSection.value = null;
    if (
      help.helpContext.value !== section ||
      manifest.clipsForSection(section).length === 0 ||
      seen.isSeen(section) ||
      !isDesktop.value ||
      help.isOpen.value ||
      isForeignDialogPresent()
    ) {
      return;
    }
    openSection.value = section;
  }

  function schedule(): void {
    clearTimer();
    if (!pendingSection.value || openSection.value || !startupReady.value) {
      return;
    }
    timer = setTimeout(evaluate, TUTORIAL_FIRST_USE_DELAY_MS);
  }

  watch(
    help.helpContext,
    (context) => {
      pendingSection.value =
        openSection.value === null && isTutorialSection(context) ? context : null;
      schedule();
    },
    { immediate: true },
  );
  watch(startupReady, schedule);

  onScopeDispose(clearTimer);

  return {
    openSection,
    openClips: computed(() =>
      openSection.value ? manifest.clipsForSection(openSection.value) : [],
    ),
    close: () => {
      const section = openSection.value;
      if (!section) {
        return;
      }
      openSection.value = null;
      seen.markSeen(section);
    },
  };
}
