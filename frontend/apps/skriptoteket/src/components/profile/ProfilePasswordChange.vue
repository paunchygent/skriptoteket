<script setup lang="ts">
import { nextTick, ref, watch } from "vue";

import { isApiError } from "../../api/client";
import { useProfile } from "../../composables/useProfile";
import { useToast } from "../../composables/useToast";

const props = defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  saved: [];
}>();

const { changePassword } = useProfile();
const toast = useToast();

const currentPassword = ref("");
const newPassword = ref("");
const confirmPassword = ref("");
const error = ref<string | null>(null);
const isSaving = ref(false);

const firstInputRef = ref<HTMLInputElement | null>(null);

function clearForm(): void {
  currentPassword.value = "";
  newPassword.value = "";
  confirmPassword.value = "";
  error.value = null;
}

function handleCancel(): void {
  clearForm();
  emit("update:modelValue", false);
}

async function handleSave(): Promise<void> {
  if (isSaving.value) return;

  error.value = null;

  if (!currentPassword.value) {
    error.value = "Ange ditt nuvarande lösenord.";
    return;
  }
  if (newPassword.value.length < 8) {
    error.value = "Lösenordet måste vara minst 8 tecken.";
    return;
  }
  if (newPassword.value !== confirmPassword.value) {
    error.value = "Lösenorden matchar inte.";
    return;
  }

  isSaving.value = true;

  try {
    await changePassword({
      current_password: currentPassword.value,
      new_password: newPassword.value,
    });
    clearForm();
    toast.success("Lösenordet uppdaterades.");
    emit("update:modelValue", false);
    emit("saved");
  } catch (err: unknown) {
    if (isApiError(err)) {
      error.value = err.message;
    } else if (err instanceof Error) {
      error.value = err.message;
    } else {
      error.value = "Kunde inte uppdatera lösenordet.";
    }
  } finally {
    isSaving.value = false;
  }
}

watch(
  () => props.modelValue,
  (isOpen) => {
    if (isOpen) {
      void nextTick(() => {
        firstInputRef.value?.focus();
      });
    } else {
      clearForm();
    }
  },
);
</script>

<template>
  <div class="password-row">
    <!-- Collapsed view: single row with label, masked value, and edit button -->
    <template v-if="!modelValue">
      <dt class="password-label">
        <svg
          class="inline-block w-4 h-4 mr-1.5 opacity-60"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
          />
        </svg>
        Lösenord
      </dt>
      <dd class="password-value">••••••••</dd>
      <div class="password-action">
        <button
          type="button"
          class="btn-inline-edit"
          @click="emit('update:modelValue', true)"
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
          Ändra
        </button>
      </div>
    </template>

    <!-- Expanded view: full password change form -->
    <template v-else>
      <dt class="password-label password-label--expanded">
        <svg
          class="inline-block w-4 h-4 mr-1.5 opacity-60"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
          />
        </svg>
        Byt lösenord
      </dt>
      <dd class="password-form-area">
        <div
          v-if="error"
          class="mb-3 text-xs text-error border-l-2 border-error pl-2 py-1 bg-error/5"
        >
          {{ error }}
        </div>

        <div class="space-y-3">
          <!-- Current password -->
          <div class="password-field">
            <label
              for="pw-current"
              class="password-field-label"
            >
              Nuvarande lösenord
            </label>
            <input
              id="pw-current"
              ref="firstInputRef"
              v-model="currentPassword"
              type="password"
              autocomplete="current-password"
              placeholder="Ange nuvarande lösenord"
              class="password-input"
              :disabled="isSaving"
            >
          </div>

          <!-- New password -->
          <div class="password-field">
            <label
              for="pw-new"
              class="password-field-label"
            >
              Nytt lösenord
            </label>
            <input
              id="pw-new"
              v-model="newPassword"
              type="password"
              autocomplete="new-password"
              placeholder="Minst 8 tecken"
              class="password-input"
              :disabled="isSaving"
            >
          </div>

          <!-- Confirm password -->
          <div class="password-field">
            <label
              for="pw-confirm"
              class="password-field-label"
            >
              Bekräfta nytt lösenord
            </label>
            <input
              id="pw-confirm"
              v-model="confirmPassword"
              type="password"
              autocomplete="new-password"
              placeholder="Upprepa det nya lösenordet"
              class="password-input"
              :disabled="isSaving"
            >
          </div>
        </div>

        <!-- Action buttons below the form -->
        <div class="password-actions">
          <button
            type="button"
            class="btn-inline-primary"
            :disabled="isSaving"
            @click="handleSave"
          >
            <svg
              v-if="!isSaving"
              class="w-4 h-4 mr-1.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span
              v-if="isSaving"
              class="w-4 h-4 mr-1.5 inline-block border-2 border-canvas/30 border-t-canvas rounded-full animate-spin"
            />
            {{ isSaving ? 'Sparar...' : 'Uppdatera lösenord' }}
          </button>
          <button
            type="button"
            class="btn-inline-cancel"
            :disabled="isSaving"
            @click="handleCancel"
          >
            Avbryt
          </button>
        </div>
      </dd>
    </template>
  </div>
</template>

<style scoped>
/* Collapsed row: 3-column grid matching other fields */
.password-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.25rem;
  padding: 0.625rem 0;
  align-items: center;
}

@media (min-width: 640px) {
  .password-row {
    grid-template-columns: 11rem 1fr 6rem;
    gap: 1rem;
  }
}

.password-label {
  display: flex;
  align-items: center;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgba(26, 43, 60, 0.7);
}

.password-label--expanded {
  align-self: start;
  padding-top: 0.25rem;
}

.password-value {
  font-size: 0.875rem;
  color: #1a2b3c;
}

.password-action {
  justify-self: end;
}

@media (max-width: 639px) {
  .password-action {
    justify-self: start;
    margin-top: 0.25rem;
  }
}

/* Expanded form area spans value + action columns */
.password-form-area {
  grid-column: 2 / -1;
}

@media (max-width: 639px) {
  .password-form-area {
    grid-column: 1 / -1;
  }
}

.password-field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.password-field-label {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgba(26, 43, 60, 0.6);
}

.password-input {
  width: 100%;
  max-width: 20rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  color: #1a2b3c;
  background: #f5f3ef;
  border: 2px solid rgba(26, 43, 60, 0.25);
  transition: border-color 150ms;
}

.password-input:focus {
  border-color: #1a2b3c;
  outline: none;
}

.password-input::placeholder {
  color: rgba(26, 43, 60, 0.4);
}

.password-input:disabled {
  opacity: 0.6;
}

.password-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 1rem;
  max-width: 20rem; /* Flush with password fields */
  justify-content: flex-start;
}
</style>
