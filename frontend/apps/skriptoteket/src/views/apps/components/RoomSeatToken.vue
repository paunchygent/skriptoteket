<script setup lang="ts">
/**
 * Shared seat token renderer.
 *
 * This component draws one circular seat marker consistently across the room
 * builder preview surfaces and the live seating canvas while leaving drag/drop
 * behavior to the parent surface.
 */

withDefaults(defineProps<{
  seatId: string;
  studentName?: string | null;
  selected?: boolean;
  ghost?: boolean;
}>(), {
  studentName: null,
  selected: false,
  ghost: false,
});
</script>

<template>
  <div
    data-test="room-seat-token"
    class="flex h-full w-full items-center justify-center rounded-full border text-center transition-transform transition-shadow"
    :class="[
      ghost
        ? 'border-2 border-dashed border-navy/60 bg-white/55 text-navy/50'
        : '',
      !ghost && selected
        ? 'border-burgundy bg-burgundy/10 text-burgundy shadow-brutal'
        : '',
      !ghost && studentName
        ? 'bg-white text-navy shadow-brutal-sm'
        : '',
      !ghost && !studentName && !selected
        ? 'border-navy/30 border-dashed bg-white/75 text-navy/45'
        : '',
    ]"
  >
    <div
      v-if="studentName"
      class="flex h-full w-full flex-col items-center justify-center px-2"
    >
      <span class="line-clamp-2 text-xs font-semibold leading-tight">
        {{ studentName }}
      </span>
      <span class="mt-1 text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
        {{ seatId }}
      </span>
    </div>
    <div
      v-else
      class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)]"
    >
      {{ seatId }}
    </div>
  </div>
</template>
