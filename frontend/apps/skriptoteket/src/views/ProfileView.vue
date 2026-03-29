<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { isApiError } from "../api/client";
import ProfileDisplay from "../components/profile/ProfileDisplay.vue";
import SystemMessage from "../components/ui/SystemMessage.vue";
import { useProfile } from "../composables/useProfile";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const { profile, load } = useProfile();

const isLoading = ref(true);
const loadError = ref<string | null>(null);

const currentEmail = computed(() => auth.user?.email ?? "");
const createdAt = computed(() => auth.user?.created_at ?? undefined);

async function loadProfile(): Promise<void> {
  isLoading.value = true;
  loadError.value = null;

  try {
    await load();
  } catch (error: unknown) {
    if (isApiError(error)) {
      loadError.value = error.message;
    } else if (error instanceof Error) {
      loadError.value = error.message;
    } else {
      loadError.value = "Kunde inte ladda profilen.";
    }
  } finally {
    isLoading.value = false;
  }
}

async function handleProfileUpdated(): Promise<void> {
  await loadProfile();
}

onMounted(() => {
  void loadProfile();
});
</script>

<template>
  <div class="space-y-6">
    <header class="expand-left-40 space-y-1">
      <h1 class="page-title">Profil</h1>
      <p class="page-description">Hantera dina personuppgifter, preferenser och lösenord.</p>
    </header>

    <SystemMessage
      v-model="loadError"
      variant="error"
      class="expand-left-40"
    />

    <div class="profile-stage">
      <Transition name="profile-fade">
        <div
          v-if="isLoading"
          key="loading"
          class="profile-stage-item expand-left-40 border border-navy bg-white shadow-brutal-sm"
        >
          <div class="flex items-center gap-4 border-b border-navy/20 p-4">
            <div class="h-14 w-14 shrink-0 animate-pulse border-2 border-navy/20 bg-navy/10" />
            <div class="flex-1 space-y-2">
              <div class="h-5 w-32 animate-pulse bg-navy/10" />
              <div class="h-4 w-48 animate-pulse bg-navy/10" />
            </div>
          </div>
          <div class="divide-y divide-navy/10 p-4">
            <div class="h-10 animate-pulse bg-navy/5" />
            <div class="h-10 animate-pulse bg-navy/5" />
            <div class="h-10 animate-pulse bg-navy/5" />
          </div>
        </div>

        <ProfileDisplay
          v-else-if="!loadError"
          key="content"
          class="profile-stage-item"
          :profile="profile"
          :email="currentEmail"
          :created-at="createdAt"
          @profile-updated="handleProfileUpdated"
        />
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.profile-stage {
  position: relative;
}

.profile-stage-item {
  width: 100%;
}

.profile-fade-enter-active,
.profile-fade-leave-active {
  transition: opacity var(--huleedu-duration-default, 200ms) var(--huleedu-ease-default, ease);
}

.profile-fade-enter-from,
.profile-fade-leave-to {
  opacity: 0;
}

.profile-stage-item.profile-fade-leave-active {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

@media (prefers-reduced-motion: reduce) {
  .profile-fade-enter-active,
  .profile-fade-leave-active {
    transition: none;
  }
}
</style>
