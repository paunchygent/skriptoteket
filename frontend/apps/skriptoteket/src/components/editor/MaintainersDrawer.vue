<script setup lang="ts">
import { ref } from "vue";
import type { components } from "../../api/openapi";

type MaintainerSummary = components["schemas"]["MaintainerSummary"];
type ApiRole = components["schemas"]["Role"];

type MaintainersDrawerProps = {
  isOpen: boolean;
  maintainers: MaintainerSummary[];
  ownerUserId: string | null;
  isSuperuser: boolean;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  success: string | null;
};

const props = defineProps<MaintainersDrawerProps>();

const emit = defineEmits<{
  (event: "close"): void;
  (event: "add", email: string): void;
  (event: "remove", userId: string): void;
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
  <Teleport to="body">
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
    class="fixed inset-y-0 right-0 z-50 w-full bg-canvas border-l border-navy shadow-brutal flex flex-col md:relative md:inset-auto md:z-auto md:w-full"
    role="dialog"
    aria-modal="true"
    aria-labelledby="maintainers-drawer-title"
  >
    <div class="p-6 border-b border-navy flex items-start justify-between gap-4">
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

    <div class="flex-1 overflow-y-auto p-6 space-y-4">
      <div
        v-if="error"
        class="p-3 border border-burgundy bg-white shadow-brutal-sm text-sm text-burgundy"
      >
        {{ error }}
      </div>
      <div
        v-else-if="success"
        class="p-3 border border-success bg-success/10 shadow-brutal-sm text-sm text-success"
      >
        {{ success }}
      </div>

      <div
        v-if="isLoading"
        class="flex items-center gap-3 text-sm text-navy/60"
      >
        <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
        <span>Laddar...</span>
      </div>

      <template v-else>
        <p
          v-if="maintainers.length === 0"
          class="text-sm text-navy/60"
        >
          Inga redigerare tilldelade.
        </p>

        <ul
          v-else
          class="space-y-2"
        >
          <li
            v-for="maintainer in maintainers"
            :key="maintainer.id"
            class="border border-navy/30 bg-white shadow-brutal-sm"
          >
            <div class="flex items-center justify-between gap-3 px-3 py-2">
              <div class="min-w-0">
                <div class="text-sm font-medium text-navy break-words">
                  {{ maintainer.email }}
                </div>
                <span
                  class="inline-block mt-1 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide border border-navy/40 text-navy/70"
                >
                  {{ roleLabel(maintainer.role) }}
                </span>
              </div>
              <button
                type="button"
                class="btn-ghost"
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

      <div class="border-t border-navy/20 pt-4">
        <form
          class="space-y-2"
          @submit.prevent="handleSubmit"
        >
          <label
            for="maintainer-email"
            class="block text-xs font-semibold uppercase tracking-wide text-navy/70"
          >
            E-post
          </label>
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
            <input
              id="maintainer-email"
              v-model="email"
              type="email"
              autocomplete="email"
              placeholder="e-post@example.com"
              class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
              :disabled="isSaving"
            >
            <button
              type="submit"
              class="btn-primary min-w-[80px]"
              :disabled="isSaving"
            >
              Lägg till
            </button>
          </div>
        </form>
      </div>
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
