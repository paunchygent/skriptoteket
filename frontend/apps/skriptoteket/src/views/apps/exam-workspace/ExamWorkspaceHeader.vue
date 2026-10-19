<script setup lang="ts">
/**
 * Exam workspace header.
 *
 * Domain purpose:
 *   The exam's title and state above every question: the title opens
 *   Provets uppgifter; the meta line shows the save state (Sparar …,
 *   Osparat, Sparat <time>), the course and the total points. The toolbar
 *   holds Öppna, Spara with Spara som, Exportera, AI facit for every
 *   question without one, and Ångra and Gör om with their shortcuts.
 *   On a phone the title block and Spara move into the shell's top bar
 *   (`#app-topbar-page-slot`), whose remaining row keeps the other tools.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView`; holds no exam state and emits every
 *     intent. Exportera comes in through the `export` slot.
 */

import { computed, ref, useId } from "vue";

import { UiGlyph } from "../../../components/ui";
import { AI_ADMIN_ONLY_NOTE, useAiAccess } from "../../../composables/useAiAccess";
import { GUEST_AI_SIGN_IN } from "./examWorkspaceGuestCopy";
import { useInjectedExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceSignIn } from "./examWorkspaceSignIn";
import ExamWorkspaceMenu from "./ExamWorkspaceMenu.vue";
import { examWorkspaceShortcut, isMacPlatform } from "./examWorkspaceFormat";

export type ExamWorkspaceSaveState = "saving" | "dirty" | "saved";

defineProps<{
  title: string | null;
  saveState: ExamWorkspaceSaveState;
  savedAt: string | null;
  courseLabel: string | null;
  total: number;
  detailsOpen: boolean;
  openDrawerOpen: boolean;
  canUndo: boolean;
  canRedo: boolean;
  canSave: boolean;
  /** An exam is open and nothing runs, so it can be copied or read again. */
  canSaveAs: boolean;
  suggestBusy: boolean;
  suggestDisabled: boolean;
  isPhone: boolean;
}>();

const emit = defineEmits<{
  toggleDetails: [];
  toggleOpen: [];
  save: [];
  saveAs: [];
  suggestAll: [];
  undo: [];
  redo: [];
}>();

const mac = isMacPlatform();
const saveKeys = mac ? "Meta+S" : "Control+S";
const saveMenuTrigger = ref<HTMLButtonElement | null>(null);
const saveMenuOpen = ref(false);
const { canUseAi } = useAiAccess();
const store = useInjectedExamWorkspaceStore();
const requestSignIn = useExamWorkspaceSignIn();
const aiNoteId = useId();
/** Guest controls stay enabled and ask for sign-in; signed-in controls follow the admin gate. */
const aiMode = computed(() =>
  store.teacher === null ? "guest" : canUseAi.value ? "allowed" : "admin_only",
);
const isGuest = computed(() => store.teacher === null);

function handleSuggestAll(): void {
  if (isGuest.value) {
    requestSignIn(GUEST_AI_SIGN_IN);
    return;
  }
  emit("suggestAll");
}

function chooseSave(action: "save" | "saveAs"): void {
  saveMenuOpen.value = false;
  if (action === "saveAs") {
    emit("saveAs");
  } else {
    emit("save");
  }
}

const SAVED_TITLE = "Provet i Mina filer har alla ändringar";
const DIRTY_TITLE = "Ändringarna sparas automatiskt som utkast. Spara skriver över provet i Mina filer.";
</script>

<template>
  <div
    class="ws-head"
    data-test="exam-workspace-header"
  >
    <Teleport
      to="#app-topbar-page-slot"
      defer
      :disabled="!isPhone"
    >
      <div class="ws-title">
        <button
          type="button"
          class="ws-title__button"
          :disabled="title === null"
          :aria-expanded="detailsOpen"
          aria-haspopup="dialog"
          title="Provets uppgifter"
          data-test="exam-workspace-title"
          @click="emit('toggleDetails')"
        >
          <span class="ws-title__text">{{ title ?? "Inget prov öppet" }}</span>
          <UiGlyph
            v-if="title !== null"
            meaning="open-list"
            :size="16"
          />
        </button>
        <div
          v-if="title !== null"
          class="ws-meta"
        >
          <span
            v-if="saveState === 'saving'"
            class="ws-meta__state"
            data-test="exam-workspace-save-state"
          >
            <UiGlyph
              meaning="busy"
              :size="16"
              class="xw-spin"
            />Sparar …
          </span>
          <span
            v-else-if="saveState === 'dirty'"
            class="ws-meta__state ws-meta__state--dirty"
            :title="DIRTY_TITLE"
            data-test="exam-workspace-save-state"
          >
            <UiGlyph
              meaning="status-modified"
              :size="16"
            />Osparat
          </span>
          <span
            v-else
            class="ws-meta__state"
            :title="SAVED_TITLE"
            data-test="exam-workspace-save-state"
          >
            <UiGlyph
              meaning="completed"
              :size="16"
            />Sparat{{ savedAt ? ` ${savedAt}` : "" }}
          </span>
          <span class="ws-meta__dot" />
          <span class="ws-meta__text">{{ courseLabel ?? "Utan kurs" }}</span>
          <span class="ws-meta__dot" />
          <span class="ws-meta__text">{{ total }} p</span>
        </div>
      </div>
    </Teleport>

    <ExamWorkspaceMenu
      :open="saveMenuOpen"
      :anchor="saveMenuTrigger"
      label="Spara"
      test-id="exam-workspace-save-options"
      @close="saveMenuOpen = false"
    >
      <button
        type="button"
        class="xw-mi"
        role="menuitem"
        :aria-disabled="!canSave || undefined"
        data-test="exam-workspace-save-option"
        @click="canSave && chooseSave('save')"
      >
        <UiGlyph
          meaning="save"
          :size="20"
        /><span class="xw-grow">Spara</span><kbd class="ws-kbd">{{ examWorkspaceShortcut("S", false, mac) }}</kbd>
      </button>
      <button
        v-if="!isGuest"
        type="button"
        class="xw-mi"
        role="menuitem"
        data-test="exam-workspace-save-as-option"
        @click="chooseSave('saveAs')"
      >
        <UiGlyph
          meaning="copy"
          :size="20"
        /><span class="xw-grow">Spara som …</span>
      </button>
    </ExamWorkspaceMenu>

    <div
      class="ws-tools"
      role="toolbar"
      aria-label="Provet"
    >
      <div
        class="ws-tools__group"
        role="group"
        aria-label="Fil"
      >
        <button
          type="button"
          class="xw-btn ws-tools__open"
          :aria-expanded="openDrawerOpen"
          aria-label="Öppna"
          title="Öppna eller importera ett prov"
          data-test="exam-workspace-open"
          @click="emit('toggleOpen')"
        >
          <UiGlyph
            meaning="open-files"
            :size="20"
          /><span class="ws-tools__word">Öppna</span>
        </button>
        <Teleport
          to="#app-topbar-page-slot"
          defer
          :disabled="!isPhone"
        >
          <div class="xw-split ws-save">
            <button
              type="button"
              class="xw-btn xw-btn--primary"
              :disabled="!canSave"
              :title="`Spara (${examWorkspaceShortcut('S', false, mac)})`"
              :aria-keyshortcuts="saveKeys"
              data-test="exam-workspace-save"
              @click="emit('save')"
            >
              <UiGlyph
                meaning="save"
                :size="20"
              />Spara
            </button>
            <button
              v-if="!isGuest"
              ref="saveMenuTrigger"
              type="button"
              class="xw-btn xw-btn--primary xw-btn--icon"
              :disabled="!canSaveAs"
              aria-haspopup="menu"
              :aria-expanded="saveMenuOpen"
              aria-label="Fler sätt att spara"
              title="Fler sätt att spara"
              data-test="exam-workspace-save-menu"
              @click="saveMenuOpen = !saveMenuOpen"
            >
              <UiGlyph
                meaning="open-list"
                :size="16"
              />
            </button>
          </div>
        </Teleport>
        <slot name="export" />
      </div>
      <span class="xw-sep" />
      <button
        type="button"
        class="xw-btn xw-btn--icon"
        :disabled="suggestDisabled || suggestBusy || aiMode === 'admin_only'"
        :title="aiMode === 'admin_only' ? AI_ADMIN_ONLY_NOTE : suggestBusy ? 'Facitförslagen tas fram …' : 'Föreslå facit för frågor som saknar facit'"
        :aria-label="suggestBusy ? 'Facitförslagen tas fram …' : 'Föreslå facit för frågor som saknar facit'"
        :aria-describedby="aiMode === 'admin_only' ? aiNoteId : undefined"
        data-test="exam-workspace-suggest-all"
        @click="handleSuggestAll"
      >
        <UiGlyph
          :meaning="suggestBusy ? 'busy' : 'ai-assist'"
          :size="20"
          :class="{ 'xw-spin': suggestBusy }"
        />
      </button>
      <span
        v-if="aiMode === 'admin_only'"
        :id="aiNoteId"
        class="xw-hint ws-tools__note"
      >{{ AI_ADMIN_ONLY_NOTE }}</span>
      <span class="xw-sep ws-tools__spacer" />
      <div
        class="ws-tools__group"
        role="group"
        aria-label="Historik"
      >
        <button
          type="button"
          class="xw-btn xw-btn--icon"
          :disabled="!canUndo"
          :title="canUndo ? `Ångra (${examWorkspaceShortcut('Z', false, mac)})` : 'Inget att ångra'"
          aria-label="Ångra"
          aria-keyshortcuts="Control+Z Meta+Z"
          data-test="exam-workspace-undo"
          @click="emit('undo')"
        >
          <UiGlyph
            meaning="undo"
            :size="20"
          />
        </button>
        <button
          type="button"
          class="xw-btn xw-btn--icon"
          :disabled="!canRedo"
          :title="canRedo ? `Gör om (${examWorkspaceShortcut('Z', true, mac)})` : 'Inget att göra om'"
          aria-label="Gör om"
          aria-keyshortcuts="Control+Shift+Z Meta+Shift+Z"
          data-test="exam-workspace-redo"
          @click="emit('redo')"
        >
          <UiGlyph
            meaning="redo"
            :size="20"
          />
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ws-head {
  display: flex; align-items: center; gap: var(--huleedu-space-4); flex: none;
  height: 60px; padding: 0 var(--huleedu-space-6); border-bottom: 1px solid var(--huleedu-surface-divider);
}
.ws-title { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.ws-title__button {
  all: unset; box-sizing: border-box; display: inline-flex; align-items: center; gap: var(--huleedu-space-1-5);
  max-width: 100%; padding: 1px var(--huleedu-space-1-5); margin-left: calc(-1 * var(--huleedu-space-1-5));
  border-radius: var(--huleedu-radius-md); cursor: pointer;
  font-size: var(--huleedu-text-lg); font-weight: var(--huleedu-font-semibold); color: var(--huleedu-navy);
}
.ws-title__button:disabled { cursor: default; color: var(--huleedu-navy-60); }
.ws-title__button svg { color: var(--huleedu-navy-60); flex: none; }
.ws-title__text { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ws-title__button:focus-visible { outline: 2px solid var(--huleedu-action-40); }
.ws-title__button[aria-expanded="true"] { background: var(--huleedu-action-10); color: var(--huleedu-action); }
@media (hover: hover) { .ws-title__button:not(:disabled):hover { background: var(--huleedu-action-05); } }
.ws-meta {
  display: flex; align-items: center; gap: var(--huleedu-space-2); min-width: 0; overflow: hidden; white-space: nowrap;
  font-size: var(--huleedu-text-xs); color: var(--huleedu-navy-60);
}
/* Sized for "Sparat 17 okt 14:05", so Osparat leaves the course in place. */
.ws-meta__state { display: inline-flex; align-items: center; gap: var(--huleedu-space-1); flex: none; min-width: 11em; }
.ws-meta__state--dirty { color: var(--huleedu-warning); font-weight: var(--huleedu-font-medium); }
.ws-meta__dot { width: 3px; height: 3px; flex: none; border-radius: 50%; background: var(--huleedu-navy-40); }
.ws-meta__text { min-width: 0; overflow: hidden; text-overflow: ellipsis; }
.ws-tools { display: flex; align-items: center; gap: var(--huleedu-space-3); flex: none; }
.ws-tools__group { display: flex; align-items: center; gap: var(--huleedu-space-2); }
.ws-tools__note { flex: 0 1 auto; min-width: 0; margin: 0; max-width: 26em; line-height: 1.35; }
.ws-kbd { font-family: var(--huleedu-font-mono); font-size: var(--huleedu-text-xs); color: var(--huleedu-navy-60); }

@media (max-width: 1279px) {
  .ws-head { padding: 0 var(--huleedu-space-4); gap: var(--huleedu-space-3); }
  .ws-tools { gap: var(--huleedu-space-2); }
  .ws-tools__word { display: none; }
  .ws-tools__open { width: var(--xw-ctl-fine, 36px); padding: 0; }
}
@media (max-width: 1279px) and (pointer: coarse) {
  .ws-tools__open { width: var(--xw-ctl, 44px); }
}
@media (max-width: 767px) {
  .ws-head { height: 52px; }
  .ws-tools { flex: 1; }
  .ws-tools__spacer { flex: 1; background: none; }
  .ws-tools__open { width: var(--xw-ctl, 44px); }
  /* In the top bar: the save state only; course and total stay in Provets uppgifter. */
  .ws-title__button { font-size: var(--huleedu-text-base); }
  .ws-meta > :not(.ws-meta__state) { display: none; }
  .ws-meta__state { min-width: 0; }
}
</style>
