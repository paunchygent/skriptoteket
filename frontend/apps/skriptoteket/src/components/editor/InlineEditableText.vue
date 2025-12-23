<script setup lang="ts">
import { nextTick, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    modelValue: string;
    placeholder?: string;
    tag?: "h1" | "p" | "span";
    displayClass?: string;
    inputClass?: string;
  }>(),
  {
    placeholder: "",
    tag: "span",
    displayClass: "",
    inputClass: "",
  },
);

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void;
}>();

const isEditing = ref(false);
const localValue = ref(props.modelValue);
const inputRef = ref<HTMLInputElement | HTMLTextAreaElement | null>(null);

watch(
  () => props.modelValue,
  (newVal) => {
    if (!isEditing.value) {
      localValue.value = newVal;
    }
  },
);

async function startEdit(): Promise<void> {
  isEditing.value = true;
  await nextTick();
  inputRef.value?.focus();
  inputRef.value?.select();
}

function commitEdit(): void {
  isEditing.value = false;
  if (localValue.value !== props.modelValue) {
    emit("update:modelValue", localValue.value);
  }
}

function cancelEdit(): void {
  localValue.value = props.modelValue;
  isEditing.value = false;
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    commitEdit();
  } else if (event.key === "Escape") {
    event.preventDefault();
    cancelEdit();
  }
}
</script>

<template>
  <div class="inline-editable-text">
    <template v-if="isEditing">
      <input
        ref="inputRef"
        v-model="localValue"
        type="text"
        :placeholder="placeholder"
        :class="[
          'w-full border border-navy bg-white px-2 py-1 text-navy shadow-brutal-sm focus:outline-none focus:ring-2 focus:ring-burgundy/30',
          inputClass,
        ]"
        @blur="commitEdit"
        @keydown="handleKeydown"
      >
    </template>
    <template v-else>
      <component
        :is="tag"
        :class="[
          'cursor-pointer hover:bg-navy/5 transition-colors rounded px-1 -mx-1',
          displayClass,
        ]"
        :title="'Klicka för att redigera'"
        @click="startEdit"
      >
        <slot>{{ modelValue || placeholder }}</slot>
      </component>
    </template>
  </div>
</template>
