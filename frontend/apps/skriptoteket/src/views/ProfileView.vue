<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { isApiError } from "../api/client";
import ProfileDisplay from "../components/profile/ProfileDisplay.vue";
import ProfileEditEmail from "../components/profile/ProfileEditEmail.vue";
import ProfileEditPassword from "../components/profile/ProfileEditPassword.vue";
import ProfileEditPersonal from "../components/profile/ProfileEditPersonal.vue";
import SystemMessage from "../components/ui/SystemMessage.vue";
import { useProfile } from "../composables/useProfile";
import { useAuthStore } from "../stores/auth";

type EditingSection = "personal" | "email" | "password" | null;

const auth = useAuthStore();
const { profile, load } = useProfile();

const isLoading = ref(true);
const loadError = ref<string | null>(null);
const editingSection = ref<EditingSection>(null);

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

function handleEditRequest(section: "personal" | "email" | "password"): void {
  editingSection.value = section;
}

function handleCancel(): void {
  editingSection.value = null;
}

async function handleSaved(): Promise<void> {
  editingSection.value = null;
  // Reload profile to get fresh data
  await loadProfile();
}

onMounted(() => {
  void loadProfile();
});
</script>

<template>
  <div class="max-w-3xl space-y-6">
    <header class="space-y-1">
      <h1 class="text-2xl font-semibold text-navy">Profil</h1>
      <p class="text-xs text-navy/70">
        Hantera dina personuppgifter, preferenser och lösenord.
      </p>
    </header>

    <SystemMessage
      v-model="loadError"
      variant="error"
    />

    <div
      v-if="isLoading"
      class="space-y-6"
    >
      <div class="h-20 animate-pulse border border-navy/20 bg-navy/5" />
      <div class="h-28 animate-pulse border border-navy/20 bg-navy/5" />
      <div class="h-16 animate-pulse border border-navy/20 bg-navy/5" />
      <div class="h-16 animate-pulse border border-navy/20 bg-navy/5" />
    </div>

    <template v-else-if="!loadError">
      <Transition
        name="profile-section"
        mode="out-in"
      >
        <ProfileDisplay
          v-if="!editingSection"
          :profile="profile"
          :email="currentEmail"
          :created-at="createdAt"
          @edit="handleEditRequest"
        />

        <ProfileEditPersonal
          v-else-if="editingSection === 'personal' && profile"
          :profile="profile"
          @cancel="handleCancel"
          @saved="handleSaved"
        />

        <ProfileEditEmail
          v-else-if="editingSection === 'email'"
          :current-email="currentEmail"
          @cancel="handleCancel"
          @saved="handleSaved"
        />

        <ProfileEditPassword
          v-else-if="editingSection === 'password'"
          @cancel="handleCancel"
          @saved="handleSaved"
        />
      </Transition>
    </template>
  </div>
</template>

<style scoped>
.profile-section-enter-active,
.profile-section-leave-active {
  transition:
    opacity var(--huleedu-duration-slow, 300ms) var(--huleedu-ease-default, ease),
    transform var(--huleedu-duration-slow, 300ms) var(--huleedu-ease-default, ease);
}

.profile-section-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.profile-section-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (prefers-reduced-motion: reduce) {
  .profile-section-enter-active,
  .profile-section-leave-active {
    transition: none;
  }
}
</style>
