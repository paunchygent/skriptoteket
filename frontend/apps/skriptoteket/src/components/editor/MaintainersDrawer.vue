<script setup lang="ts">
import { computed, ref } from "vue";
import type { components } from "../../api/openapi";

import SystemMessage from "../ui/SystemMessage.vue";

type MaintainerSummary = components["schemas"]["MaintainerSummary"];
type ApiRole = components["schemas"]["Role"];

type MaintainersDrawerProps = {
  isOpen: boolean;
  variant?: "drawer" | "panel";
  maintainers: MaintainerSummary[];
  ownerUserId: string | null;
  isSuperuser: boolean;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
};

const props = withDefaults(defineProps<MaintainersDrawerProps>(), {
  variant: "drawer",
});

const isPanel = computed(() => props.variant === "panel");

const emit = defineEmits<{
  (event: "close"): void;
  (event: "add", email: string): void;
  (event: "remove", userId: string): void;
  (event: "update:error", value: string | null): void;
}>();

const email = ref("");

function handleSubmit(): void {
  emit("add", email.value);
}

function roleLabel(role: ApiRole): string {
  return role.toUpperCase();
}

function isRemovalBlocked(maintainer: MaintainerSummary): boolean {
  if (props.isSuperuser) {
    return false;
  }
  if (props.ownerUserId && maintainer.id === props.ownerUserId) {
    return true;
  }
  return maintainer.role === "superuser";
}

function removalBlockedReason(maintainer: MaintainerSummary): string | null {
  if (props.isSuperuser) {
    return null;
  }
  if (props.ownerUserId && maintainer.id === props.ownerUserId) {
    return "Endast superuser kan ändra ägarens redigeringsbehörigheter.";
  }
  if (maintainer.role === "superuser") {
    return "Endast superuser kan ändra superuser-behörigheter.";
  }
  return null;
}
</script>

<template>
  <!-- Mobile backdrop -->
  <Teleport
    v-if="!isPanel"
    to="body"
  >
    <Transition name="drawer-backdrop">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-40 bg-navy/40 md:hidden"
        @click="emit('close')"
      />
    </Transition>
  </Teleport>

  <!-- Drawer - direct grid participant on desktop -->
  <aside
    :class="[
      isPanel
        ? 'relative w-full bg-white border border-navy/20 shadow-brutal-sm flex flex-col min-h-0'
        : 'fixed inset-y-0 right-0 z-50 w-full bg-canvas border-l border-navy shadow-brutal flex flex-col md:relative md:inset-auto md:z-auto md:w-full md:h-full md:overflow-hidden',
    ]"
    :role="isPanel ? 'region' : 'dialog'"
    :aria-modal="!isPanel"
    aria-labelledby="maintainers-drawer-title"
  >
    <div
      v-if="isPanel"
      class="border-b border-navy/20 px-3 py-2 flex items-center justify-between gap-3"
    >
      <span
        id="maintainers-drawer-title"
        class="text-[10px] font-semibold uppercase tracking-wide text-navy/60"
      >
        Beh&ouml;righeter
      </span>
    </div>

    <div
      v-else
      class="border-b border-navy flex items-start justify-between gap-4 p-4"
    >
      <div>
        <h2
          id="maintainers-drawer-title"
          class="text-lg font-semibold text-navy"
        >
          Ändra redigeringsbehörigheter
        </h2>
        <p class="text-sm text-navy/70">
          Lägg till eller ta bort användare som får redigera verktyget.
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

    <div
      :class="[
        isPanel ? 'p-3 space-y-3' : 'flex-1 overflow-y-auto p-4 space-y-4',
      ]"
    >
      <SystemMessage
        v-if="error"
        :model-value="error"
        variant="error"
        @update:model-value="emit('update:error', $event)"
      />

      <div
        v-if="isLoading"
        class="flex items-center gap-3 text-[11px] text-navy/60"
      >
        <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
        <span>Laddar...</span>
      </div>

      <template v-else>
        <div class="border-b border-navy/20 pb-3">
          <form
            class="space-y-2"
            @submit.prevent="handleSubmit"
          >
            <label
              for="maintainer-email"
              class="block text-[10px] font-semibold uppercase tracking-wide text-navy/60"
            >
              L&auml;gg till redigerare
            </label>
            <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
              <input
                id="maintainer-email"
                v-model="email"
                type="email"
                autocomplete="email"
                placeholder="e-post@example.com"
                class="w-full h-[28px] border border-navy/30 bg-white px-2.5 text-[11px] text-navy shadow-none"
                :disabled="isSaving"
              >
              <button
                type="submit"
                class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none min-w-[84px]"
                :disabled="isSaving"
              >
                L&auml;gg till
              </button>
            </div>
          </form>
        </div>

        <p
          v-if="maintainers.length === 0"
          class="text-[11px] text-navy/60"
        >
          Inga redigerare tilldelade.
        </p>

        <ul
          v-else
          class="space-y-1.5"
        >
          <li
            v-for="maintainer in maintainers"
            :key="maintainer.id"
            class="border border-navy/30 bg-white shadow-none"
          >
            <div class="flex items-center justify-between gap-3 px-2.5 py-2">
              <div class="min-w-0">
                <div class="text-[11px] font-medium text-navy break-words">
                  {{ maintainer.email }}
                </div>
                <span
                  class="inline-block mt-1 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide border border-navy/40 text-navy/70"
                >
                  {{ roleLabel(maintainer.role) }}
                </span>
              </div>
              <button
                type="button"
                class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none"
                :disabled="isSaving || isRemovalBlocked(maintainer)"
                :title="removalBlockedReason(maintainer) ?? undefined"
                @click="emit('remove', maintainer.id)"
              >
                Ta bort
              </button>
            </div>
          </li>
        </ul>
      </template>
    </div>
  </aside>
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
