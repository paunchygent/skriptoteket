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
  compareVersionId?: string | null;
  canCompare?: boolean;
  canRollback?: boolean;
  isSubmitting?: boolean;
  checkpoints: EditorWorkingCopyCheckpointSummary[];
};

const props = withDefaults(defineProps<VersionHistoryDrawerProps>(), {
  activeVersionId: null,
  compareVersionId: null,
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
  (event: "restoreCheckpoint", checkpointId: string): void;
  (event: "removeCheckpoint", checkpointId: string): void;
  (event: "restoreServerVersion"): void;
}>();

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
    ? "fixed inset-y-[var(--huleedu-space-8)] left-[var(--huleedu-space-4)] right-[var(--huleedu-space-4)] z-50 bg-canvas border border-navy flex flex-col overflow-hidden md:left-[var(--huleedu-space-12)] md:right-auto md:w-[420px]"
    : "fixed inset-y-0 right-0 z-50 w-full bg-canvas border-l border-navy flex flex-col md:relative md:inset-auto md:z-auto md:w-full md:h-full md:overflow-hidden",
);

function versionLabel(state: VersionState): string {
  const labels: Record<VersionState, string> = {
    draft: "utkast",
    in_review: "granskning",
    active: "publicerad",
    archived: "arkiverad",
  };
  return labels[state] ?? state;
}

function formatDateTime(value: string | number): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  const formatted = new Intl.DateTimeFormat("sv-SE", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
  return formatted.replace(",", "");
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
  return label || "återställningspunkt";
}

function checkpointKindLabel(kind: EditorWorkingCopyCheckpointSummary["kind"]): string {
  return kind === "pinned" ? "manuell" : "auto";
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
        <div class="px-3 py-2 border-b border-navy/20 bg-canvas flex items-start justify-between gap-4">
          <div class="space-y-0.5">
            <h2
              id="history-drawer-title"
              class="text-xs font-semibold uppercase tracking-wide text-navy/70"
            >
              Öppna sparade
            </h2>
            <p class="text-[11px] text-navy/60">
              Serverversioner och återställningspunkter.
            </p>
          </div>
          <button
            type="button"
            class="btn-ghost h-[28px] w-[28px] px-0 py-0 text-[12px] font-semibold normal-case tracking-normal shadow-none border-navy/30 bg-white leading-none"
            @click="emit('close')"
          >
            ✕
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-3 space-y-3">
          <div class="space-y-1">
            <h3 class="text-[10px] font-semibold uppercase tracking-wide text-navy/70">
              Serverversioner
            </h3>
            <p class="text-[11px] text-navy/60">
              Välj en version att öppna. Arkiverad = äldre version (kan återställas).
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
            class="border border-navy/20 bg-white divide-y divide-navy/20"
          >
            <li
              v-for="version in visibleVersions"
              :key="version.id"
              :class="[
                'group transition-colors',
                version.id === activeVersionId
                  ? 'bg-navy/5 border-l-2 border-navy/60'
                  : props.compareVersionId && version.id === props.compareVersionId
                    ? 'bg-canvas/30 border-l-2 border-navy/40'
                    : 'hover:bg-canvas/30',
              ]"
            >
              <div class="grid grid-cols-[minmax(0,1fr)_64px_56px_72px] items-center gap-2 px-2 py-1">
                <button
                  type="button"
                  class="text-left w-full min-w-0"
                  @click="handleSelect(version.id)"
                >
                  <div class="min-w-0">
                    <div class="flex items-center gap-2 min-w-0">
                      <span class="text-[11px] font-semibold text-navy">
                        v{{ version.version_number }}
                      </span>
                      <span class="text-[11px] text-navy/60 whitespace-nowrap">
                        {{ formatDateTime(version.created_at) }}
                      </span>
                    </div>
                  </div>
                </button>

                <div class="justify-self-end">
                  <span class="text-[10px] font-medium text-navy/50 whitespace-nowrap">
                    {{ versionLabel(version.state) }}
                  </span>
                </div>

                <div class="justify-self-end">
                  <button
                    v-if="canCompare && version.id !== activeVersionId"
                    type="button"
                    class="h-[20px] w-full text-right text-[11px] font-semibold text-navy/70 hover:text-navy hover:underline hover:underline-offset-4 disabled:text-navy/30 disabled:no-underline"
                    :disabled="isSubmitting"
                    @click.stop="handleCompare(version.id)"
                  >
                    jämför
                  </button>
                </div>

                <div class="justify-self-end">
                  <button
                    v-if="canRollback && version.state === 'archived'"
                    type="button"
                    class="h-[20px] w-full text-right text-[11px] font-semibold text-navy/70 hover:text-navy hover:underline hover:underline-offset-4 disabled:text-navy/30 disabled:no-underline"
                    :disabled="isSubmitting"
                    @click.stop="handleRollback(version.id)"
                  >
                    återställ
                  </button>
                </div>
              </div>
            </li>
          </ul>

          <button
            v-if="hasMoreVersions"
            type="button"
            class="btn-ghost h-[24px] px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-white leading-none"
            @click="showAllVersions = !showAllVersions"
          >
            {{ showAllVersions ? "visa färre" : "visa fler" }}
          </button>

          <div class="border-t border-navy/20 pt-4 mt-4 space-y-3">
            <div class="space-y-1">
              <h3 class="text-[10px] font-semibold uppercase tracking-wide text-navy/70">
                Återställningspunkter
              </h3>
              <p class="text-[11px] text-navy/60">
                Sparas i webbläsaren.
              </p>
            </div>

            <p
              v-if="checkpoints.length === 0"
              class="text-sm text-navy/60"
            >
              Inga återställningspunkter ännu.
            </p>

            <ul
              v-else
              class="border border-navy/20 bg-white divide-y divide-navy/20"
            >
              <li
                v-for="checkpoint in checkpoints"
                :key="checkpoint.id"
                class="px-2 py-1.5"
              >
                <div class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2">
                  <div>
                    <div class="text-[11px] font-semibold text-navy">
                      {{ formatCheckpointLabel(checkpoint.label) }}
                    </div>
                    <div class="text-[11px] text-navy/60">
                      {{ formatDateTime(checkpoint.createdAt) }}
                      · {{ checkpointKindLabel(checkpoint.kind) }}
                    </div>
                  </div>

                  <div class="flex items-center justify-end justify-self-end gap-3">
                    <button
                      v-if="checkpoint.kind === 'pinned'"
                      type="button"
                      class="h-[20px] text-[11px] font-semibold text-navy/70 hover:text-navy hover:underline hover:underline-offset-4 disabled:text-navy/30 disabled:no-underline"
                      :disabled="isSubmitting"
                      @click="emit('removeCheckpoint', checkpoint.id)"
                    >
                      ta bort
                    </button>
                    <button
                      type="button"
                      class="h-[20px] text-[11px] font-semibold text-navy/70 hover:text-navy hover:underline hover:underline-offset-4 disabled:text-navy/30 disabled:no-underline"
                      :disabled="isSubmitting"
                      @click="emit('restoreCheckpoint', checkpoint.id)"
                    >
                      återställ
                    </button>
                  </div>
                </div>
              </li>
            </ul>

            <button
              type="button"
              class="text-left text-[11px] font-semibold text-navy/70 hover:text-navy hover:underline hover:underline-offset-4 disabled:text-navy/30 disabled:no-underline"
              :disabled="isSubmitting"
              @click="emit('restoreServerVersion')"
            >
              återställ serverversion (rensa återställningspunkter)
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
