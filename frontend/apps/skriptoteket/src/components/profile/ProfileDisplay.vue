<script setup lang="ts">
import { computed, ref, reactive, watch } from "vue";

import { isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { useProfile } from "../../composables/useProfile";
import { useToast } from "../../composables/useToast";
import ProfileAiSettingsInline from "./ProfileAiSettingsInline.vue";

type UserProfile = components["schemas"]["UserProfile"];

const props = defineProps<{
  profile: UserProfile | null;
  email: string;
  createdAt?: string;
}>();

const emit = defineEmits<{
  profileUpdated: [];
}>();

const { updateProfile } = useProfile();
const toast = useToast();

// Section-level edit states (toggle behavior)
const isEditingPersonal = ref(false);
const isSaving = ref(false);

// Ref to AI settings component
const aiSettingsRef = ref<InstanceType<typeof ProfileAiSettingsInline> | null>(null);
const isEditingAi = ref(false);

// Edit form data for personal info section
const personalForm = reactive({
  first_name: "",
  last_name: "",
  display_name: "",
  locale: "sv-SE",
});

const initials = computed(() => {
  const first = props.profile?.first_name?.[0] ?? "";
  const last = props.profile?.last_name?.[0] ?? "";
  if (first || last) return (first + last).toUpperCase();
  return props.email[0]?.toUpperCase() ?? "?";
});

const displayName = computed(() => {
  if (props.profile?.display_name) return props.profile.display_name;
  if (props.profile?.first_name || props.profile?.last_name) {
    return `${props.profile.first_name ?? ""} ${props.profile.last_name ?? ""}`.trim();
  }
  return props.email.split("@")[0];
});

const memberSince = computed(() => {
  if (!props.createdAt) return null;
  try {
    const date = new Date(props.createdAt);
    return date.toLocaleDateString("sv-SE", { year: "numeric", month: "long" });
  } catch {
    return null;
  }
});

const localeOptions = [
  { value: "sv-SE", label: "Svenska (sv-SE)" },
  { value: "en-US", label: "English (en-US)" },
];

// Toggle editing personal info
function toggleEditingPersonal(): void {
  if (!isEditingPersonal.value) {
    personalForm.first_name = props.profile?.first_name ?? "";
    personalForm.last_name = props.profile?.last_name ?? "";
    personalForm.display_name = props.profile?.display_name ?? "";
    personalForm.locale = props.profile?.locale ?? "sv-SE";
  }
  isEditingPersonal.value = !isEditingPersonal.value;
}

// cancelEditingPersonal removed - toggle button handles close

async function savePersonalInfo(): Promise<void> {
  if (isSaving.value) return;
  isSaving.value = true;
  try {
    await updateProfile({
      first_name: personalForm.first_name.trim() || null,
      last_name: personalForm.last_name.trim() || null,
      display_name: personalForm.display_name.trim() || null,
      locale: personalForm.locale,
    });
    toast.success("Profilen uppdaterades.");
    emit("profileUpdated");
    isEditingPersonal.value = false;
  } catch (err: unknown) {
    const message = isApiError(err) ? err.message : "Kunde inte spara.";
    toast.failure(message);
  } finally {
    isSaving.value = false;
  }
}

// Toggle AI settings editing - sync with child component
function toggleEditingAi(): void {
  isEditingAi.value = !isEditingAi.value;
  if (isEditingAi.value) {
    aiSettingsRef.value?.startEditing();
  } else {
    aiSettingsRef.value?.cancelEditing();
  }
}

// Sync form when profile changes
watch(() => props.profile, () => {
  if (!isEditingPersonal.value) {
    personalForm.first_name = props.profile?.first_name ?? "";
    personalForm.last_name = props.profile?.last_name ?? "";
    personalForm.display_name = props.profile?.display_name ?? "";
    personalForm.locale = props.profile?.locale ?? "sv-SE";
  }
}, { immediate: true });

</script>

<template>
  <div class="profile-panel border border-navy bg-white shadow-brutal-sm">
    <!-- Header with avatar -->
    <div class="flex items-center gap-4 border-b border-navy/20 p-4">
      <div
        class="flex h-14 w-14 shrink-0 items-center justify-center border-2 border-navy/30 bg-navy text-xl font-bold text-canvas"
      >
        {{ initials }}
      </div>
      <div class="min-w-0 space-y-0.5">
        <h2 class="truncate text-lg font-semibold text-navy">{{ displayName }}</h2>
        <p class="truncate text-sm text-navy/70">{{ email }}</p>
        <p
          v-if="memberSince"
          class="text-xs text-navy/50"
        >
          Medlem sedan {{ memberSince }}
        </p>
      </div>
    </div>

    <!-- Personal Information section -->
    <section class="border-b border-navy/20">
      <div class="section-header">
        <h3 class="section-title">Personlig information</h3>
        <button
          type="button"
          class="btn-inline-edit"
          @click="toggleEditingPersonal"
        >
          <svg
            class="w-3 h-3 mr-1"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
            />
          </svg>
          {{ isEditingPersonal ? 'Stäng' : 'Ändra' }}
        </button>
      </div>

      <!-- Read-only view -->
      <dl
        v-if="!isEditingPersonal"
        class="section-fields"
      >
        <div class="field-row">
          <dt class="field-label">Förnamn</dt>
          <dd class="field-value">{{ profile?.first_name || '–' }}</dd>
        </div>
        <div class="field-row">
          <dt class="field-label">Efternamn</dt>
          <dd class="field-value">{{ profile?.last_name || '–' }}</dd>
        </div>
        <div class="field-row">
          <dt class="field-label">Visningsnamn</dt>
          <dd class="field-value">{{ profile?.display_name || '–' }}</dd>
        </div>
        <div class="field-row">
          <dt class="field-label">Språk</dt>
          <dd class="field-value">{{ localeOptions.find(o => o.value === (profile?.locale ?? 'sv-SE'))?.label ?? profile?.locale }}</dd>
        </div>
      </dl>

      <!-- Edit form -->
      <div
        v-else
        class="section-edit-form"
      >
        <div class="edit-field">
          <label
            for="edit-first-name"
            class="edit-field-label"
          >Förnamn</label>
          <input
            id="edit-first-name"
            v-model="personalForm.first_name"
            type="text"
            class="input-inline"
            :disabled="isSaving"
          >
        </div>
        <div class="edit-field">
          <label
            for="edit-last-name"
            class="edit-field-label"
          >Efternamn</label>
          <input
            id="edit-last-name"
            v-model="personalForm.last_name"
            type="text"
            class="input-inline"
            :disabled="isSaving"
          >
        </div>
        <div class="edit-field">
          <label
            for="edit-display-name"
            class="edit-field-label"
          >Visningsnamn</label>
          <input
            id="edit-display-name"
            v-model="personalForm.display_name"
            type="text"
            class="input-inline"
            placeholder="Valfritt"
            :disabled="isSaving"
          >
        </div>
        <div class="edit-field">
          <label
            for="edit-locale"
            class="edit-field-label"
          >Språk</label>
          <select
            id="edit-locale"
            v-model="personalForm.locale"
            class="input-inline"
            :disabled="isSaving"
          >
            <option
              v-for="opt in localeOptions"
              :key="opt.value"
              :value="opt.value"
            >
              {{ opt.label }}
            </option>
          </select>
        </div>
        <div class="section-actions">
          <button
            type="button"
            class="btn-inline-primary"
            :disabled="isSaving"
            @click="savePersonalInfo"
          >
            {{ isSaving ? 'Sparar...' : 'Spara ändringar' }}
          </button>
        </div>
      </div>
    </section>

    <!-- Account section -->
    <section class="border-b border-navy/20">
      <div class="section-header">
        <h3 class="section-title">Konto</h3>
      </div>

      <dl class="section-fields">
        <div class="field-row">
          <dt class="field-label">E-post</dt>
          <dd class="field-value">{{ email }}</dd>
        </div>
        <div class="field-row">
          <dt class="field-label">Inloggning</dt>
          <dd class="field-value">
            Hanteras via inloggningen för Skriptoteket. Kontakta administratören
            för Skriptoteket vid ändringar.
          </dd>
        </div>
      </dl>
    </section>

    <!-- AI Settings section -->
    <section>
      <div class="section-header">
        <h3 class="section-title">AI-inställningar</h3>
        <button
          type="button"
          class="btn-inline-edit"
          @click="toggleEditingAi"
        >
          <svg
            class="w-3 h-3 mr-1"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
            />
          </svg>
          {{ isEditingAi ? 'Stäng' : 'Ändra' }}
        </button>
      </div>

      <div class="px-4 pb-2">
        <ProfileAiSettingsInline ref="aiSettingsRef" />
      </div>
    </section>
  </div>
</template>

<style scoped>
.profile-panel {
  width: 100%;
  max-width: 44rem;
}

/* Section header with title and optional edit button */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.625rem 1rem;
  background: rgba(245, 243, 239, 0.5); /* canvas/50 */
}

.section-title {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgba(26, 43, 60, 0.7);
}

/* Read-only fields list */
.section-fields {
  padding: 0 1rem;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.25rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(26, 43, 60, 0.1);
}

.field-row:last-child {
  border-bottom: none;
}

@media (min-width: 640px) {
  .field-row {
    grid-template-columns: 11rem 1fr auto;
    gap: 1rem;
    align-items: center;
  }
}

.field-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgba(26, 43, 60, 0.7);
}

.field-value {
  font-size: 0.875rem;
  color: #1a2b3c;
}

.field-action {
  justify-self: end;
}

@media (max-width: 639px) {
  .field-action {
    justify-self: start;
    margin-top: 0.25rem;
  }
}

/* Edit form within section */
.section-edit-form {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.edit-field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

@media (min-width: 640px) {
  .edit-field {
    flex-direction: row;
    align-items: center;
    gap: 1rem;
  }

  .edit-field-label {
    width: 10rem;
    flex-shrink: 0;
  }
}

.edit-field-label {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgba(26, 43, 60, 0.6);
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(26, 43, 60, 0.1);
}

@media (min-width: 640px) {
  .section-actions {
    padding-left: 11rem;
  }
}
</style>
