<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { isApiError } from "../api/client";
import { useProfile } from "../composables/useProfile";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const { profile, load, updateProfile, changePassword, changeEmail } = useProfile();

const isLoading = ref(true);
const loadError = ref<string | null>(null);

const firstName = ref("");
const lastName = ref("");
const displayName = ref("");
const locale = ref("sv-SE");

const profileError = ref<string | null>(null);
const profileSuccess = ref<string | null>(null);
const isSavingProfile = ref(false);

const newEmail = ref("");
const emailError = ref<string | null>(null);
const emailSuccess = ref<string | null>(null);
const isSavingEmail = ref(false);

const currentPassword = ref("");
const newPassword = ref("");
const confirmPassword = ref("");
const passwordError = ref<string | null>(null);
const passwordSuccess = ref<string | null>(null);
const isSavingPassword = ref(false);

const currentEmail = computed(() => auth.user?.email ?? "");

function syncProfileForm(): void {
  if (!profile.value) return;
  firstName.value = profile.value.first_name ?? "";
  lastName.value = profile.value.last_name ?? "";
  displayName.value = profile.value.display_name ?? "";
  locale.value = profile.value.locale ?? "sv-SE";
}

async function loadProfile(): Promise<void> {
  isLoading.value = true;
  loadError.value = null;

  try {
    await load();
    syncProfileForm();
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

async function saveProfile(): Promise<void> {
  if (isSavingProfile.value) return;

  profileError.value = null;
  profileSuccess.value = null;

  if (!firstName.value.trim() || !lastName.value.trim()) {
    profileError.value = "Förnamn och efternamn krävs.";
    return;
  }

  isSavingProfile.value = true;

  try {
    await updateProfile({
      first_name: firstName.value,
      last_name: lastName.value,
      display_name: displayName.value,
      locale: locale.value,
    });
    profileSuccess.value = "Profilen uppdaterades.";
  } catch (error: unknown) {
    if (isApiError(error)) {
      profileError.value = error.message;
    } else if (error instanceof Error) {
      profileError.value = error.message;
    } else {
      profileError.value = "Kunde inte uppdatera profilen.";
    }
  } finally {
    isSavingProfile.value = false;
  }
}

async function saveEmail(): Promise<void> {
  if (isSavingEmail.value) return;

  emailError.value = null;
  emailSuccess.value = null;

  const trimmed = newEmail.value.trim().toLowerCase();
  if (!trimmed) {
    emailError.value = "Ange en ny e-postadress.";
    return;
  }
  if (trimmed === currentEmail.value.toLowerCase()) {
    emailError.value = "E-postadressen är redan registrerad.";
    return;
  }

  isSavingEmail.value = true;

  try {
    await changeEmail({ email: trimmed });
    newEmail.value = "";
    emailSuccess.value = "E-postadressen uppdaterades.";
  } catch (error: unknown) {
    if (isApiError(error)) {
      emailError.value = error.message;
    } else if (error instanceof Error) {
      emailError.value = error.message;
    } else {
      emailError.value = "Kunde inte uppdatera e-postadressen.";
    }
  } finally {
    isSavingEmail.value = false;
  }
}

async function savePassword(): Promise<void> {
  if (isSavingPassword.value) return;

  passwordError.value = null;
  passwordSuccess.value = null;

  if (newPassword.value.length < 8) {
    passwordError.value = "Lösenordet måste vara minst 8 tecken.";
    return;
  }
  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = "Lösenorden matchar inte.";
    return;
  }

  isSavingPassword.value = true;

  try {
    await changePassword({
      current_password: currentPassword.value,
      new_password: newPassword.value,
    });
    currentPassword.value = "";
    newPassword.value = "";
    confirmPassword.value = "";
    passwordSuccess.value = "Lösenordet uppdaterades.";
  } catch (error: unknown) {
    if (isApiError(error)) {
      passwordError.value = error.message;
    } else if (error instanceof Error) {
      passwordError.value = error.message;
    } else {
      passwordError.value = "Kunde inte uppdatera lösenordet.";
    }
  } finally {
    isSavingPassword.value = false;
  }
}

onMounted(() => {
  void loadProfile();
});
</script>

<template>
  <div class="max-w-3xl space-y-8">
    <header class="space-y-2">
      <h1 class="text-2xl font-semibold text-navy">Profil</h1>
      <p class="text-sm text-navy/70">
        Hantera dina personuppgifter, preferenser och lösenord.
      </p>
    </header>

    <div
      v-if="loadError"
      class="p-3 border border-burgundy bg-white shadow-brutal-sm text-burgundy text-sm"
    >
      {{ loadError }}
    </div>

    <div
      v-if="isLoading"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
    >
      Laddar profil...
    </div>

    <template v-else>
      <section class="border border-navy bg-white shadow-brutal-sm p-5 space-y-4">
        <div class="space-y-1">
          <h2 class="text-lg font-semibold text-navy">Personlig information</h2>
          <p class="text-sm text-navy/60">Uppdatera namn och visningsnamn.</p>
        </div>

        <div
          v-if="profileError"
          class="p-3 border border-burgundy bg-white text-burgundy text-sm"
        >
          {{ profileError }}
        </div>

        <div
          v-if="profileSuccess"
          class="p-3 border border-success bg-success/10 text-success text-sm"
        >
          {{ profileSuccess }}
        </div>

        <form
          class="space-y-4"
          @submit.prevent="saveProfile"
        >
          <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-2">
              <label
                for="profile-first-name"
                class="text-sm font-semibold text-navy"
              >Förnamn</label>
              <input
                id="profile-first-name"
                v-model="firstName"
                type="text"
                required
                class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
                :disabled="isSavingProfile"
              >
            </div>
            <div class="space-y-2">
              <label
                for="profile-last-name"
                class="text-sm font-semibold text-navy"
              >Efternamn</label>
              <input
                id="profile-last-name"
                v-model="lastName"
                type="text"
                required
                class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
                :disabled="isSavingProfile"
              >
            </div>
          </div>

          <div class="space-y-2">
            <label
              for="profile-display-name"
              class="text-sm font-semibold text-navy"
            >Visningsnamn</label>
            <input
              id="profile-display-name"
              v-model="displayName"
              type="text"
              placeholder="Valfritt"
              class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
              :disabled="isSavingProfile"
            >
          </div>

          <div class="space-y-2">
            <label
              for="profile-locale"
              class="text-sm font-semibold text-navy"
            >Språk</label>
            <select
              id="profile-locale"
              v-model="locale"
              class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
              :disabled="isSavingProfile"
            >
              <option value="sv-SE">Svenska (sv-SE)</option>
              <option value="en-US">English (en-US)</option>
            </select>
          </div>

          <button
            type="submit"
            class="px-4 py-2 bg-navy text-canvas border border-navy shadow-brutal-sm font-semibold uppercase tracking-wide hover:bg-burgundy transition-colors disabled:opacity-50"
            :disabled="isSavingProfile"
          >
            {{ isSavingProfile ? "Sparar…" : "Spara" }}
          </button>
        </form>
      </section>

      <section class="border border-navy bg-white shadow-brutal-sm p-5 space-y-4">
        <div class="space-y-1">
          <h2 class="text-lg font-semibold text-navy">E-postadress</h2>
          <p class="text-sm text-navy/60">Nuvarande: {{ currentEmail }}</p>
        </div>

        <div
          v-if="emailError"
          class="p-3 border border-burgundy bg-white text-burgundy text-sm"
        >
          {{ emailError }}
        </div>

        <div
          v-if="emailSuccess"
          class="p-3 border border-success bg-success/10 text-success text-sm"
        >
          {{ emailSuccess }}
        </div>

        <form
          class="space-y-4"
          @submit.prevent="saveEmail"
        >
          <div class="space-y-2">
            <label
              for="profile-email"
              class="text-sm font-semibold text-navy"
            >Ny e-post</label>
            <input
              id="profile-email"
              v-model="newEmail"
              type="email"
              autocomplete="email"
              class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
              :disabled="isSavingEmail"
            >
          </div>

          <button
            type="submit"
            class="px-4 py-2 bg-navy text-canvas border border-navy shadow-brutal-sm font-semibold uppercase tracking-wide hover:bg-burgundy transition-colors disabled:opacity-50"
            :disabled="isSavingEmail"
          >
            {{ isSavingEmail ? "Sparar…" : "Uppdatera e-post" }}
          </button>
        </form>
      </section>

      <section class="border border-navy bg-white shadow-brutal-sm p-5 space-y-4">
        <div class="space-y-1">
          <h2 class="text-lg font-semibold text-navy">Ändra lösenord</h2>
          <p class="text-sm text-navy/60">
            Ange ditt nuvarande lösenord och välj ett nytt.
          </p>
        </div>

        <div
          v-if="passwordError"
          class="p-3 border border-burgundy bg-white text-burgundy text-sm"
        >
          {{ passwordError }}
        </div>

        <div
          v-if="passwordSuccess"
          class="p-3 border border-success bg-success/10 text-success text-sm"
        >
          {{ passwordSuccess }}
        </div>

        <form
          class="space-y-4"
          @submit.prevent="savePassword"
        >
          <div class="space-y-2">
            <label
              for="current-password"
              class="text-sm font-semibold text-navy"
            >Nuvarande lösenord</label>
            <input
              id="current-password"
              v-model="currentPassword"
              type="password"
              autocomplete="current-password"
              class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
              :disabled="isSavingPassword"
            >
          </div>

          <div class="space-y-2">
            <label
              for="new-password"
              class="text-sm font-semibold text-navy"
            >Nytt lösenord</label>
            <input
              id="new-password"
              v-model="newPassword"
              type="password"
              autocomplete="new-password"
              class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
              :disabled="isSavingPassword"
            >
            <p class="text-xs text-navy/60">Minst 8 tecken.</p>
          </div>

          <div class="space-y-2">
            <label
              for="confirm-password"
              class="text-sm font-semibold text-navy"
            >Bekräfta nytt lösenord</label>
            <input
              id="confirm-password"
              v-model="confirmPassword"
              type="password"
              autocomplete="new-password"
              class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
              :disabled="isSavingPassword"
            >
          </div>

          <button
            type="submit"
            class="px-4 py-2 bg-navy text-canvas border border-navy shadow-brutal-sm font-semibold uppercase tracking-wide hover:bg-burgundy transition-colors disabled:opacity-50"
            :disabled="isSavingPassword"
          >
            {{ isSavingPassword ? "Sparar…" : "Uppdatera lösenord" }}
          </button>
        </form>
      </section>
    </template>
  </div>
</template>
