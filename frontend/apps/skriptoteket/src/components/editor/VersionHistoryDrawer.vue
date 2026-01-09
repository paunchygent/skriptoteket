<script setup lang="ts">
import { computed, ref } from "vue";
import type { components } from "../../api/openapi";
import type { EditorWorkingCopyCheckpointSummary } from "../../composables/editor/useEditorWorkingCopy";

type EditorVersionSummary = components["schemas"]["EditorVersionSummary"];
type VersionState = components["schemas"]["VersionState"];

type VersionHistoryDrawerProps = {
  isOpen: boolean;
  variant?: "drawer" | "popover";
  versions: EditorVersionSummary[];
  activeVersionId?: string | null;
  canCompare?: boolean;
  canRollback?: boolean;
  isSubmitting?: boolean;
  checkpoints: EditorWorkingCopyCheckpointSummary[];
  pinnedCheckpointCount: number;
  pinnedCheckpointLimit: number;
  isCheckpointBusy: boolean;
};

const props = withDefaults(defineProps<VersionHistoryDrawerProps>(), {
  activeVersionId: null,
  canCompare: true,
  canRollback: false,
  isSubmitting: false,
  variant: "drawer",
});

const emit = defineEmits<{
  (event: "close"): void;
  (event: "select", versionId: string): void;
  (event: "compare", versionId: string): void;
  (event: "rollback", versionId: string): void;
  (event: "createCheckpoint", label: string): void;
  (event: "restoreCheckpoint", checkpointId: string): void;
  (event: "removeCheckpoint", checkpointId: string): void;
  (event: "restoreServerVersion"): void;
}>();

const checkpointLabel = ref("");
const showAllVersions = ref(false);
const VERSION_PREVIEW_LIMIT = 12;

const visibleVersions = computed(() => {
  if (showAllVersions.value) {
    return props.versions;
  }
  return props.versions.slice(0, VERSION_PREVIEW_LIMIT);
});

const hasMoreVersions = computed(() => props.versions.length > VERSION_PREVIEW_LIMIT);
const isPopover = computed(() => props.variant === "popover");
const panelClasses = computed(() =>
  isPopover.value
    ? "fixed inset-y-[var(--huleedu-space-8)] left-[var(--huleedu-space-4)] right-[var(--huleedu-space-4)] z-50 bg-canvas border border-navy shadow-brutal flex flex-col overflow-hidden md:left-[var(--huleedu-space-12)] md:right-auto md:w-[420px]"
    : "fixed inset-y-0 right-0 z-50 w-full bg-canvas border-l border-navy shadow-brutal flex flex-col md:relative md:inset-auto md:z-auto md:w-full md:h-full md:overflow-hidden",
);

function versionLabel(state: VersionState): string {
  const labels: Record<VersionState, string> = {
    draft: "Arbetsversion",
    in_review: "Granskning",
    active: "Publicerad",
    archived: "Arkiverad",
  };
  return labels[state] ?? state;
}

function formatDateTime(value: string | number): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString("sv-SE", { dateStyle: "medium", timeStyle: "short" });
}

function handleSelect(versionId: string): void {
  emit("select", versionId);
}

function handleRollback(versionId: string): void {
  emit("rollback", versionId);
}

function handleCompare(versionId: string): void {
  emit("compare", versionId);
}

function formatCheckpointLabel(label: string): string {
  return label || "Återställningspunkt";
}

function checkpointKindLabel(kind: EditorWorkingCopyCheckpointSummary["kind"]): string {
  return kind === "pinned" ? "Manuell" : "Auto";
}

function handleCreateCheckpoint(): void {
  emit("createCheckpoint", checkpointLabel.value.trim());
  checkpointLabel.value = "";
}
</script>

<template>
  <Teleport
    to="body"
    :disabled="!isPopover"
  >
    <Transition name="drawer-backdrop">
      <div
        v-if="isOpen && isPopover"
        class="fixed inset-0 z-40 bg-navy/40"
        @click="emit('close')"
      />
    </Transition>
    <Transition name="drawer-backdrop">
      <div
        v-if="isOpen && !isPopover"
        class="fixed inset-0 z-40 bg-navy/40 md:hidden"
        @click="emit('close')"
      />
    </Transition>

    <Transition name="drawer-slide">
      <aside
        v-if="isOpen"
        :class="panelClasses"
        role="dialog"
        aria-modal="true"
        aria-labelledby="history-drawer-title"
      >
        <div class="p-4 border-b border-navy flex items-start justify-between gap-4">
          <div>
            <h2
              id="history-drawer-title"
              class="text-lg font-semibold text-navy"
            >
              Öppna sparade
            </h2>
            <p class="text-sm text-navy/70">
              Serverversioner och lokala återställningspunkter.
            </p>
          </div>
          <button
            type="button"
            class="text-navy/60 hover:text-navy text-2xl leading-none"
            @click="emit('close')"
          >
            &times;
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-4 space-y-3">
          <div class="space-y-1">
            <h3 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
              Serverversioner
            </h3>
            <p class="text-xs text-navy/60">
              Välj en version att öppna eller jämföra.
            </p>
          </div>
          <p
            v-if="versions.length === 0"
            class="text-sm text-navy/60"
          >
            Inga versioner ännu.
          </p>

          <ul
            v-else
            class="space-y-2"
          >
            <li
              v-for="version in visibleVersions"
              :key="version.id"
              :class="[
                'border shadow-brutal-sm transition-colors',
                version.id === activeVersionId
                  ? 'border-burgundy bg-burgundy/5'
                  : 'border-navy/30 bg-white hover:bg-canvas hover:border-navy',
              ]"
            >
              <div class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-2 py-2">
                <button
                  type="button"
                  class="flex items-center justify-between gap-3 text-left w-full"
                  @click="handleSelect(version.id)"
                >
                  <div>
                    <div class="text-xs font-semibold text-navy">
                      v{{ version.version_number }}
                    </div>
                    <div class="text-[10px] text-navy/60">
                      {{ formatDateTime(version.created_at) }}
                    </div>
                  </div>
                  <span
                    :class="[
                      'px-2 py-0.5 border text-[10px] font-semibold uppercase tracking-wide',
                      version.id === activeVersionId
                        ? 'border-burgundy text-burgundy'
                        : 'border-navy/40 text-navy/70',
                    ]"
                  >
                    {{ versionLabel(version.state) }}
                  </span>
                </button>

                <div class="flex flex-wrap items-center justify-end gap-2">
                  <button
                    v-if="canCompare && version.id !== activeVersionId"
                    type="button"
                    class="btn-ghost px-2 py-1 text-[10px] font-semibold tracking-wide"
                    :disabled="isSubmitting"
                    @click.stop="handleCompare(version.id)"
                  >
                    Diff
                  </button>

                  <button
                    v-if="canRollback && version.state === 'archived'"
                    type="button"
                    class="btn-ghost px-2 py-1 text-[10px] font-semibold tracking-wide"
                    :disabled="isSubmitting"
                    @click.stop="handleRollback(version.id)"
                  >
                    Återställ
                  </button>
                </div>
              </div>
            </li>
          </ul>

          <button
            v-if="hasMoreVersions"
            type="button"
            class="btn-ghost px-2 py-1 text-[10px] font-semibold tracking-wide"
            @click="showAllVersions = !showAllVersions"
          >
            {{ showAllVersions ? "Visa färre" : "Visa fler" }}
          </button>

          <div class="border-t border-navy/20 pt-4 mt-4 space-y-3">
            <div class="space-y-1">
              <h3 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
                Lokala återställningspunkter
              </h3>
              <p class="text-sm text-navy/60">
                Återställningspunkter sparas lokalt i webbläsaren.
              </p>
            </div>

            <div class="space-y-2">
              <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
                Ny återställningspunkt (manuell)
              </label>
              <div class="flex flex-wrap gap-2">
                <input
                  v-model="checkpointLabel"
                  type="text"
                  class="flex-1 min-w-[160px] border border-navy bg-white px-3 py-2 text-xs text-navy shadow-brutal-sm"
                  placeholder="Etikett (valfri)"
                >
                <button
                  type="button"
                  class="btn-ghost px-2 py-1 text-[10px] font-semibold tracking-wide"
                  :disabled="
                    isCheckpointBusy || pinnedCheckpointCount >= pinnedCheckpointLimit || isSubmitting
                  "
                  @click="handleCreateCheckpoint"
                >
                  Skapa återställningspunkt
                </button>
              </div>
              <p
                v-if="pinnedCheckpointCount >= pinnedCheckpointLimit"
                class="text-xs text-burgundy"
              >
                Du har nått maxgränsen för manuella återställningspunkter ({{ pinnedCheckpointLimit }}).
              </p>
            </div>

            <p
              v-if="checkpoints.length === 0"
              class="text-sm text-navy/60"
            >
              Inga lokala återställningspunkter ännu.
            </p>

            <ul
              v-else
              class="space-y-2"
            >
              <li
                v-for="checkpoint in checkpoints"
                :key="checkpoint.id"
                class="border border-navy/30 bg-white shadow-brutal-sm px-3 py-2"
              >
                <div class="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div class="text-sm font-semibold text-navy">
                      {{ formatCheckpointLabel(checkpoint.label) }}
                    </div>
                    <div class="text-xs text-navy/60">
                      {{ formatDateTime(checkpoint.createdAt) }}
                      · {{ checkpointKindLabel(checkpoint.kind) }}
                    </div>
                  </div>

                  <div class="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      class="btn-ghost px-2 py-1 text-[10px] font-semibold tracking-wide"
                      :disabled="isSubmitting"
                      @click="emit('restoreCheckpoint', checkpoint.id)"
                    >
                      Återställ
                    </button>
                    <button
                      v-if="checkpoint.kind === 'pinned'"
                      type="button"
                      class="btn-ghost px-2 py-1 text-[10px] font-semibold tracking-wide"
                      :disabled="isSubmitting"
                      @click="emit('removeCheckpoint', checkpoint.id)"
                    >
                      Ta bort
                    </button>
                  </div>
                </div>
              </li>
            </ul>

            <button
              type="button"
              class="btn-ghost px-2 py-1 text-[10px] font-semibold tracking-wide"
              :disabled="isSubmitting"
              @click="emit('restoreServerVersion')"
            >
              Återställ till serverversion (rensa lokalt)
            </button>
          </div>
        </div>
      </aside>
    </Transition>
  </Teleport>
</template>

<style scoped>
.drawer-backdrop-enter-active,
.drawer-backdrop-leave-active {
  transition: opacity var(--huleedu-duration-slow) var(--huleedu-ease-default);
}
.drawer-backdrop-enter-from,
.drawer-backdrop-leave-to {
  opacity: 0;
}

.drawer-slide-enter-active,
.drawer-slide-leave-active {
  transition: transform var(--huleedu-duration-slow) var(--huleedu-ease-default),
    opacity var(--huleedu-duration-slow) var(--huleedu-ease-default);
}
.drawer-slide-enter-from,
.drawer-slide-leave-to {
  transform: translateX(8%);
  opacity: 0;
}
</style>
