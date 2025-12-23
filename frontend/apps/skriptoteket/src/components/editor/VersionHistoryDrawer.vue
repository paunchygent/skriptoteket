<script setup lang="ts">
import type { components } from "../../api/openapi";

type EditorVersionSummary = components["schemas"]["EditorVersionSummary"];

type VersionHistoryDrawerProps = {
  isOpen: boolean;
  versions: EditorVersionSummary[];
  activeVersionId?: string | null;
};

withDefaults(defineProps<VersionHistoryDrawerProps>(), {
  activeVersionId: null,
});

const emit = defineEmits<{
  (event: "close"): void;
  (event: "select", versionId: string): void;
}>();

type VersionState = components["schemas"]["VersionState"];

function versionLabel(state: VersionState): string {
  const labels: Record<VersionState, string> = {
    draft: "Utkast",
    in_review: "Granskning",
    active: "Publicerad",
    archived: "Arkiverad",
  };
  return labels[state] ?? state;
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("sv-SE", { dateStyle: "medium", timeStyle: "short" });
}

function handleSelect(versionId: string): void {
  emit("select", versionId);
}
</script>

<template>
  <Transition name="drawer-backdrop">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-40 bg-navy/40 md:hidden"
      @click="emit('close')"
    />
  </Transition>

  <Transition name="drawer-slide">
    <aside
      v-if="isOpen"
      class="fixed inset-y-0 right-0 z-50 w-full bg-canvas border-l border-navy shadow-brutal flex flex-col md:static md:z-auto md:w-full"
      role="dialog"
      aria-modal="true"
      aria-labelledby="history-drawer-title"
    >
      <div class="p-6 border-b border-navy flex items-start justify-between gap-4">
        <div>
          <h2
            id="history-drawer-title"
            class="text-lg font-semibold text-navy"
          >
            Öppna sparade
          </h2>
          <p class="text-sm text-navy/70">
            Välj en tidigare version att öppna.
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

      <div class="flex-1 overflow-y-auto p-6 space-y-3">
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
            v-for="version in versions"
            :key="version.id"
            class="border border-navy/30 bg-white shadow-brutal-sm"
          >
            <RouterLink
              :to="`/admin/tool-versions/${version.id}`"
              class="flex items-center justify-between gap-3 px-3 py-2"
              @click="handleSelect(version.id)"
            >
              <div>
                <div class="text-sm font-semibold text-navy">
                  v{{ version.version_number }}
                </div>
                <div class="text-xs text-navy/60">
                  {{ formatDateTime(version.created_at) }}
                </div>
              </div>
              <span
                :class="[
                  'px-2 py-0.5 border text-xs font-semibold uppercase tracking-wide',
                  version.id === activeVersionId
                    ? 'border-burgundy text-burgundy'
                    : 'border-navy/40 text-navy/70',
                ]"
              >
                {{ versionLabel(version.state) }}
              </span>
            </RouterLink>
          </li>
        </ul>
      </div>
    </aside>
  </Transition>
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
