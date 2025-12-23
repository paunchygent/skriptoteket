<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

type WorkflowAction = "submit_review" | "publish" | "request_changes" | "rollback";

type ActionItem = {
  id: WorkflowAction;
  label: string;
  tone?: "primary" | "danger";
};

type WorkflowActionsDropdownProps = {
  items: ActionItem[];
  label?: string;
};

const props = withDefaults(defineProps<WorkflowActionsDropdownProps>(), {
  label: "Åtgärder",
});

const emit = defineEmits<{ (event: "select", value: WorkflowAction): void }>();

const isOpen = ref(false);
const dropdownRef = ref<HTMLElement | null>(null);

const hasItems = computed(() => props.items.length > 0);

function toggleMenu(): void {
  if (!hasItems.value) return;
  isOpen.value = !isOpen.value;
}

function closeMenu(): void {
  isOpen.value = false;
}

function handleSelect(item: ActionItem): void {
  emit("select", item.id);
  closeMenu();
}

function handleDocumentClick(event: MouseEvent): void {
  const target = event.target as Node | null;
  if (!target || !dropdownRef.value) return;
  if (!dropdownRef.value.contains(target)) {
    closeMenu();
  }
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    closeMenu();
  }
}

onMounted(() => {
  document.addEventListener("click", handleDocumentClick);
  document.addEventListener("keydown", handleKeydown);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleDocumentClick);
  document.removeEventListener("keydown", handleKeydown);
});
</script>

<template>
  <div
    ref="dropdownRef"
    class="relative"
  >
    <button
      type="button"
      class="px-3 py-2 text-xs font-semibold uppercase tracking-wide border border-navy bg-white text-navy shadow-brutal-sm hover:bg-canvas btn-secondary-hover transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none"
      :class="{ 'opacity-60 cursor-not-allowed': !hasItems }"
      :disabled="!hasItems"
      :aria-expanded="isOpen"
      aria-haspopup="menu"
      @click="toggleMenu"
    >
      {{ label }}
      <span class="ml-1">▾</span>
    </button>

    <div
      v-if="isOpen"
      class="absolute right-0 mt-2 w-56 border border-navy bg-canvas shadow-brutal-sm z-20"
      role="menu"
    >
      <button
        v-for="item in items"
        :key="item.id"
        type="button"
        role="menuitem"
        class="w-full text-left px-3 py-2 text-sm text-navy hover:bg-white transition-colors"
        :class="{
          'text-burgundy': item.tone === 'danger',
          'font-semibold': item.tone === 'primary',
        }"
        @click="handleSelect(item)"
      >
        {{ item.label }}
      </button>
    </div>
  </div>
</template>
