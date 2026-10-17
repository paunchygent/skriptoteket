<script setup lang="ts">
import { computed, ref } from "vue";
import type { components } from "../../api/openapi";

import { SystemMessage, UiDenseActionButton, UiDenseSpinner, UiDenseStatusPill, UiGlyph } from "../ui";

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
        ? 'relative w-full panel-inset flex flex-col min-h-0'
        : 'fixed inset-y-0 right-0 z-50 w-full bg-modal border-l border-navy/20 shadow-md flex flex-col md:relative md:inset-auto md:z-auto md:w-full md:h-full md:overflow-hidden',
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
      class="border-b border-navy/20 flex items-start justify-between gap-4 p-4"
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
      <UiDenseActionButton
        label="Stäng"
        icon-only
        @click="emit('close')"
      >
        <template #leading>
          <UiGlyph
            meaning="close"
            :size="16"
          />
        </template>
      </UiDenseActionButton>
    </div>

    <div
      :class="[
        isPanel ? 'p-3 space-y-3' : 'flex-1 overflow-y-auto p-4 space-y-4',
      ]"
    >
      <SystemMessage
        v-if="error"
        :model-value="error"
        tone="failure"
        dismissible
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
        @update:model-value="emit('update:error', $event)"
      />

      <div
        v-if="isLoading"
        class="flex items-center gap-3 text-[11px] text-navy/60"
      >
        <UiDenseSpinner :size="16" />
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
                class="w-full h-[28px] border border-navy/30 bg-panel px-2.5 text-[11px] text-navy shadow-none"
                :disabled="isSaving"
              >
              <UiDenseActionButton
                type="submit"
                label="Lägg till"
                :disabled="isSaving"
              />
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
            class="border border-navy/30 bg-panel shadow-none"
          >
            <div class="flex items-center justify-between gap-3 px-2.5 py-2">
              <div class="min-w-0">
                <div class="text-[11px] font-medium text-navy break-words">
                  {{ maintainer.email }}
                </div>
                <div class="mt-1">
                  <UiDenseStatusPill :label="roleLabel(maintainer.role)" />
                </div>
              </div>
              <UiDenseActionButton
                label="Ta bort"
                :disabled="isSaving || isRemovalBlocked(maintainer)"
                :title="removalBlockedReason(maintainer) ?? undefined"
                @click="emit('remove', maintainer.id)"
              />
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
