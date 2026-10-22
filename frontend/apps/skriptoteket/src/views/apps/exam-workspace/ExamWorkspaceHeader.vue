<script setup lang="ts">
/**
 * Exam workspace header.
 *
 * Domain purpose:
 *   One row above every question: the title block (title, pencil and the
 *   plain course and points line), the Uppgifter command that opens Provets
 *   uppgifter, the file commands (Nytt prov, Öppna, Spara som …, Exportera, Importera),
 *   PDF, the AI glyph and the fixed-width autosave status slot (Sparat, Sparar …, Inte sparat). Clicking
 *   the title or the pencil renames the exam in place: Enter or blur commits,
 *   Escape restores. On a phone the title block moves into the shell's top bar
 *   (`#app-topbar-page-slot`).
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView`; holds no exam state and emits every
 *     intent. Exportera comes in through the `export` slot.
 *   - Undo and redo live in the editor toolbar; their shortcuts are owned by
 *     TASK-SKRIPT-40-04-14.
 */

import { computed, nextTick, ref } from "vue";

import { UiGlyph } from "../../../components/ui";
import { AI_ADMIN_ONLY_NOTE } from "../../../composables/useAiAccess";
import { GUEST_AI_SIGN_IN } from "./examWorkspaceGuestCopy";
import { aiDailyLimitNote, aiDailyLimitReached } from "./aiDailyLimit";
import { useExamWorkspaceSignIn } from "./examWorkspaceSignIn";
import { useExamWorkspaceAiMode } from "./useExamWorkspaceAiMode";

export type ExamWorkspaceSaveState = "saving" | "saved" | "unsaved";

const props = defineProps<{
  title: string | null;
  saveState: ExamWorkspaceSaveState;
  saveText: string;
  /** The status tooltip: the `Inte sparat` reason, or the saved confirmation. */
  saveTitle: string | null;
  courseLabel: string | null;
  total: number;
  detailsOpen: boolean;
  openDrawerOpen: boolean;
  /** The exam is open and editable, so its title can be renamed. */
  canRename: boolean;
  /** An exam is open and nothing runs, so it can be copied or read again. */
  canSaveAs: boolean;
  suggestBusy: boolean;
  suggestDisabled: boolean;
  isPhone: boolean;
  /** A new exam is being created; the Nytt prov command locks while it runs. */
  newExamBusy: boolean;
  /** The Förhandsgranska panel is open beside the editor. */
  previewOpen: boolean;
}>();

const emit = defineEmits<{
  toggleDetails: [];
  toggleOpen: [];
  newExam: [];
  saveAs: [];
  importFile: [];
  suggestAll: [];
  togglePreview: [];
  renameTitle: [title: string];
}>();

const requestSignIn = useExamWorkspaceSignIn();
/** Guest controls stay enabled and ask for sign-in; signed-in controls follow the admin gate. */
const aiMode = useExamWorkspaceAiMode();
const isGuest = computed(() => aiMode.value === "guest");
/** The door's daily limit disables the suggest-all button for the page session. */
const limitReached = aiDailyLimitReached;

const editingTitle = ref(false);
const draft = ref("");
const titleInput = ref<HTMLInputElement | null>(null);

async function startRename(): Promise<void> {
  if (!props.canRename || props.title === null || editingTitle.value) return;
  draft.value = props.title;
  editingTitle.value = true;
  await nextTick();
  titleInput.value?.focus();
  titleInput.value?.select();
}

/** Enter and blur both commit; the flag keeps the blur after Enter or Escape from committing twice. */
function commitRename(): void {
  if (!editingTitle.value) return;
  editingTitle.value = false;
  const next = draft.value.replace(/\s+/g, " ").trim();
  if (next !== "" && next !== props.title) emit("renameTitle", next);
}

function cancelRename(): void {
  editingTitle.value = false;
}

function handleSuggestAll(): void {
  if (limitReached.value) {
    return;
  }
  if (isGuest.value) {
    requestSignIn(GUEST_AI_SIGN_IN);
    return;
  }
  emit("suggestAll");
}
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
        <div class="ws-title__row">
          <input
            v-if="editingTitle"
            ref="titleInput"
            v-model="draft"
            type="text"
            class="ws-title__input"
            aria-label="Provets namn"
            data-test="exam-workspace-title-input"
            @keydown.enter.prevent="commitRename"
            @keydown.esc.prevent="cancelRename"
            @blur="commitRename"
          >
          <template v-else>
            <button
              type="button"
              class="ws-title__button"
              :disabled="title === null || !canRename"
              :title="title ?? undefined"
              data-test="exam-workspace-title"
              @click="startRename"
            >
              <span class="ws-title__text">{{ title ?? "Inget prov öppet" }}</span>
            </button>
            <button
              v-if="title !== null"
              type="button"
              class="xw-tool"
              :disabled="!canRename"
              title="Byt namn på provet"
              aria-label="Byt namn på provet"
              data-test="exam-workspace-rename"
              @click="startRename"
            >
              <UiGlyph
                meaning="edit"
                :size="16"
              />
            </button>
          </template>
        </div>
        <p
          v-if="title !== null"
          class="ws-meta"
          data-test="exam-workspace-meta"
        >
          {{ courseLabel ?? "Utan kurs" }} · {{ total }} p
        </p>
      </div>
    </Teleport>

    <div
      class="ws-tools"
      role="toolbar"
      aria-label="Provet"
    >
      <template v-if="title !== null">
        <button
          type="button"
          class="xw-cmd"
          :aria-expanded="detailsOpen"
          aria-haspopup="dialog"
          aria-label="Provets uppgifter"
          title="Provets uppgifter"
          data-test="exam-workspace-details"
          @click="emit('toggleDetails')"
        >
          <UiGlyph
            meaning="info"
            :size="20"
          /><span class="ws-word">Uppgifter</span>
        </button>
        <span class="xw-toolsep" />
      </template>
      <button
        type="button"
        class="xw-cmd"
        aria-label="Nytt prov"
        title="Skapa ett nytt prov"
        data-test="exam-workspace-new-exam"
        :disabled="newExamBusy"
        @click="emit('newExam')"
      >
        <UiGlyph
          meaning="file-new"
          :size="20"
        /><span class="ws-word">Nytt prov</span>
      </button>
      <button
        type="button"
        class="xw-cmd"
        :aria-expanded="openDrawerOpen"
        aria-label="Öppna"
        title="Öppna eller importera ett prov"
        data-test="exam-workspace-open"
        @click="emit('toggleOpen')"
      >
        <UiGlyph
          meaning="open-files"
          :size="20"
        /><span class="ws-word">Öppna</span>
      </button>
      <button
        v-if="!isGuest"
        type="button"
        class="xw-cmd"
        :disabled="!canSaveAs"
        aria-label="Spara som …"
        title="Spara som …"
        data-test="exam-workspace-save-as-command"
        @click="emit('saveAs')"
      >
        <UiGlyph
          meaning="copy"
          :size="20"
        /><span class="ws-word">Spara som</span>
      </button>
      <slot name="export" />
      <button
        type="button"
        class="xw-cmd"
        aria-label="Importera prov"
        title="Importera prov"
        data-test="exam-workspace-import"
        @click="emit('importFile')"
      >
        <UiGlyph
          meaning="file-import"
          :size="20"
        /><span class="ws-word">Importera</span>
      </button>
      <template v-if="!isPhone && !isGuest">
        <span class="xw-toolsep" />
        <button
          type="button"
          class="xw-cmd"
          :aria-pressed="previewOpen"
          aria-label="Förhandsgranska PDF"
          title="Förhandsgranska PDF"
          data-test="exam-workspace-print-preview-toggle"
          @click="emit('togglePreview')"
        >
          <UiGlyph
            meaning="preview"
            :size="20"
          /><span class="ws-word">PDF</span>
        </button>
      </template>
      <button
        type="button"
        class="xw-cmd"
        :disabled="suggestDisabled || suggestBusy || aiMode === 'admin_only' || limitReached"
        :title="limitReached ? (aiDailyLimitNote ?? undefined) : aiMode === 'admin_only' ? AI_ADMIN_ONLY_NOTE : suggestBusy ? 'Facitförslagen tas fram …' : 'Föreslå facit för frågor som saknar facit'"
        :aria-label="suggestBusy ? 'Facitförslagen tas fram …' : 'Föreslå facit för frågor som saknar facit'"
        :aria-description="limitReached ? (aiDailyLimitNote ?? undefined) : aiMode === 'admin_only' ? AI_ADMIN_ONLY_NOTE : undefined"
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
        v-if="limitReached"
        class="ws-limit"
        data-test="ai-daily-limit-note"
      >{{ aiDailyLimitNote }}</span>
      <span class="ws-status-slot">
        <span
          v-if="title !== null"
          class="ws-status"
          role="status"
          :title="saveTitle ?? undefined"
          data-test="exam-workspace-save-state"
        >
          <UiGlyph
            :meaning="saveState === 'saving' ? 'autosave-saving' : saveState === 'unsaved' ? 'blocker' : 'autosave-saved'"
            :size="20"
            :class="{ 'xw-spin': saveState === 'saving' }"
          /><span class="ws-status__text">{{ saveText }}</span>
        </span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.ws-head {
  display: flex; align-items: center; gap: var(--huleedu-space-4); flex: none;
  height: 60px; padding: 0 var(--huleedu-space-6); border-bottom: 1px solid var(--huleedu-surface-divider);
}
.ws-title { flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: flex-start; gap: 1px; }
.ws-title__row { display: flex; align-items: center; gap: var(--huleedu-space-1); max-width: 100%; min-width: 0; }
.ws-title__button {
  all: unset; box-sizing: border-box; min-width: 0; cursor: pointer; border-radius: var(--huleedu-radius-md);
  font-size: var(--huleedu-text-base); font-weight: var(--huleedu-font-semibold); color: var(--huleedu-navy);
}
.ws-title__button:disabled { cursor: default; color: var(--huleedu-navy-60); }
.ws-title__text { display: block; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ws-title__button:focus-visible { outline: 2px solid var(--huleedu-action-40); }
.ws-title__input {
  box-sizing: border-box; width: min(28em, 100%); font: inherit; font-size: var(--huleedu-text-base);
  font-weight: var(--huleedu-font-semibold); color: var(--huleedu-navy); padding: 0 var(--huleedu-space-1-5);
  border: 1px solid var(--huleedu-action); border-radius: var(--huleedu-radius-md); background: var(--huleedu-surface-content);
}
.ws-title__input:focus-visible { outline: 2px solid var(--huleedu-action-40); outline-offset: 0; }
.ws-meta {
  margin: 0; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  font-size: var(--huleedu-text-xs); color: var(--huleedu-navy-70);
}
.ws-tools { display: flex; align-items: center; gap: var(--huleedu-space-2); flex: none; }
/* Sized for its widest state ("Sparat 14:05"), so no state moves a neighbouring control. */
.ws-status-slot { display: flex; align-items: center; flex: none; width: 8.5rem; margin-left: var(--huleedu-space-2); }
.ws-status {
  display: inline-flex; align-items: center; gap: var(--huleedu-space-1-5); min-width: 0; font-size: var(--huleedu-type-control-value-size); color: var(--huleedu-navy-70);
  white-space: nowrap;
}
.ws-status svg { flex: none; }
.ws-status__text { min-width: 0; overflow: hidden; text-overflow: ellipsis; }
/* The daily-limit note sits next to the suggest-all button for the page
   session; two lines at most so the toolbar keeps its height. */
.ws-limit {
  max-width: 16rem; font-size: var(--huleedu-text-xs); color: var(--huleedu-navy-70);
  line-height: 1.35;
}

@media (max-width: 1279px) {
  .ws-head { padding: 0 var(--huleedu-space-4); gap: var(--huleedu-space-3); }
  .ws-word { display: none; }
}
@media (max-width: 767px) {
  .ws-head { height: 52px; }
  .ws-tools { flex: 1; justify-content: flex-end; }
  .ws-limit { max-width: 9rem; }
  /* Glyph only on a phone; the text stays for assistive technology and the tooltip. */
  .ws-status-slot { width: auto; margin-left: 0; }
  .ws-status__text { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
}
</style>
