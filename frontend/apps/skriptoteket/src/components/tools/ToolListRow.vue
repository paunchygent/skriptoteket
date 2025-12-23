<script setup lang="ts">
type Props = {
  gridClass?: string;
  mainClass?: string;
  statusClass?: string;
  actionsClass?: string;
};

const props = withDefaults(defineProps<Props>(), {
  gridClass: "",
  mainClass: "space-y-1 min-w-0",
  statusClass: "justify-self-start sm:justify-self-center",
  actionsClass: "justify-self-start sm:justify-self-end",
});
</script>

<template>
  <li
    :class="['p-4 grid gap-2 sm:gap-4 items-center', props.gridClass]"
  >
    <div :class="props.mainClass">
      <slot name="main" />
    </div>
    <div :class="props.statusClass">
      <slot name="status" />
    </div>
    <div :class="props.actionsClass">
      <slot name="actions" />
    </div>
  </li>
</template>
