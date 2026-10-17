<script setup lang="ts">
import { computed, nextTick, ref, useId, watch } from "vue";
import { UiGlyph } from "../ui/shared";

const props = withDefaults(
  defineProps<{
    label: string;
    value: string;
    placeholder?: string;
    type?: "text" | "email" | "password" | "select";
    options?: Array<{ value: string; label: string }>;
    editable?: boolean;
    saving?: boolean;
    maskValue?: boolean;
  }>(),
  {
    placeholder: "–",
    type: "text",
    options: () => [],
    editable: true,
    saving: false,
    maskValue: false,
  },
);

const emit = defineEmits<{
  save: [value: string];
  cancel: [];
}>();

const labelId = useId();
const isEditing = ref(false);
const editValue = ref("");
const inputRef = ref<HTMLInputElement | HTMLSelectElement | null>(null);

const displayValue = computed(() => {
  if (props.maskValue) return "••••••••";
  return props.value || props.placeholder;
});

const isEmpty = computed(() => !props.value);

function startEditing(): void {
  if (!props.editable || props.saving) return;
  editValue.value = props.value;
  isEditing.value = true;
  void nextTick(() => {
    inputRef.value?.focus();
    if (inputRef.value instanceof HTMLInputElement) {
      inputRef.value.select();
    }
  });
}

function handleSave(): void {
  if (props.saving) return;
  emit("save", editValue.value);
}

function handleCancel(): void {
  isEditing.value = false;
  editValue.value = "";
  emit("cancel");
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    handleCancel();
  } else if (event.key === "Enter" && props.type !== "select") {
    handleSave();
  }
}

watch(
  () => props.saving,
  (saving) => {
    if (!saving && isEditing.value) {
      isEditing.value = false;
    }
  },
);
</script>

<template>
  <div class="profile-field-row">
    <dt
      :id="labelId"
      class="profile-field-label"
    >
      {{ label }}
    </dt>
    <dd class="profile-field-value">
      <span class="field-edit-stage">
        <Transition name="field-edit">
          <span
            v-if="!isEditing"
            :key="'display'"
            class="field-edit-surface"
            :class="isEmpty ? 'text-navy/50 italic' : 'text-navy'"
          >{{ displayValue }}</span>

          <div
            v-else
            :key="'edit'"
            class="field-edit-surface flex items-center gap-2"
          >
            <select
              v-if="type === 'select'"
              ref="inputRef"
              v-model="editValue"
              :aria-labelledby="labelId"
              class="w-full max-w-[200px] border border-[var(--huleedu-panel-border)] bg-canvas px-2 py-1 text-sm text-navy focus:border-navy focus:outline-none"
              :disabled="saving"
              @keydown="handleKeydown"
            >
              <option
                v-for="opt in options"
                :key="opt.value"
                :value="opt.value"
              >
                {{ opt.label }}
              </option>
            </select>
            <input
              v-else
              ref="inputRef"
              v-model="editValue"
              :aria-labelledby="labelId"
              :type="type"
              class="w-full max-w-[200px] border border-[var(--huleedu-panel-border)] bg-canvas px-2 py-1 text-sm text-navy focus:border-navy focus:outline-none"
              :disabled="saving"
              @keydown="handleKeydown"
            >
          </div>
        </Transition>
      </span>
    </dd>
    <div class="profile-field-action">
      <span class="field-edit-stage">
        <Transition name="field-edit">
          <button
            v-if="!isEditing && editable"
            :key="'edit-btn'"
            type="button"
            class="field-edit-surface btn-inline-edit"
            :disabled="saving"
            @click="startEditing"
          >
            <UiGlyph
              meaning="edit"
              :size="12"
            />
            Ändra
          </button>

          <div
            v-else-if="isEditing"
            :key="'save-btns'"
            class="field-edit-surface flex items-center gap-1.5"
          >
            <button
              type="button"
              class="btn-inline-edit"
              :disabled="saving"
              @click="handleSave"
            >
              {{ saving ? '...' : 'Spara' }}
            </button>
            <button
              type="button"
              class="btn-inline-edit"
              :disabled="saving"
              @click="handleCancel"
            >
              Avbryt
            </button>
          </div>
        </Transition>
      </span>
    </div>
  </div>
</template>

<style scoped>
.profile-field-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.25rem;
  padding: 0.625rem 0;
  align-items: baseline;
}

@media (min-width: 640px) {
  .profile-field-row {
    grid-template-columns: 11rem 1fr 6rem;
    gap: 1rem;
    align-items: center;
  }
}

.profile-field-label {
  font-size: var(--huleedu-text-xs);
  font-weight: var(--huleedu-font-semibold);
  text-transform: uppercase;
  letter-spacing: var(--huleedu-tracking-label);
  color: var(--huleedu-navy-70);
}

.profile-field-value {
  font-size: var(--huleedu-text-sm);
  color: var(--huleedu-navy);
  min-height: 1.5rem;
}

.profile-field-action {
  justify-self: end;
}

@media (max-width: 639px) {
  .profile-field-action {
    justify-self: start;
    margin-top: 0.25rem;
  }
}

.field-edit-stage {
  position: relative;
  display: inline-flex;
  max-width: 100%;
}

.field-edit-surface {
  max-width: 100%;
}

.field-edit-enter-active,
.field-edit-leave-active {
  transition: opacity var(--huleedu-duration-fast, 150ms) var(--huleedu-ease-default, ease);
}

.field-edit-enter-from,
.field-edit-leave-to {
  opacity: 0;
}

.field-edit-surface.field-edit-leave-active {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

@media (prefers-reduced-motion: reduce) {
  .field-edit-enter-active,
  .field-edit-leave-active {
    transition: none;
  }
}
</style>
