<script setup lang="ts">
/**
 * Planner workspace shell.
 *
 * This component renders the active classroom-planning workspace after a draft
 * has been created or resumed. It keeps the default surface focused on one
 * teacher task at a time so grouping and seating do not teach a shared
 * whole-workspace mental model.
 */

import { computed, ref } from "vue";

import GroupBoard from "./GroupBoard.vue";
import PlannerMetadataDrawer from "./PlannerMetadataDrawer.vue";
import RoomCanvas from "./RoomCanvas.vue";
import { useClassroomState } from "../useClassroomState";

type PlannerView = "groups" | "seats";

const emit = defineEmits<{
  (e: "reset-selection"): void;
}>();

const plannerState = useClassroomState();

const currentView = ref<PlannerView>("groups");
const selectedStudentId = ref<string | null>(null);
const isMetadataDrawerOpen = ref(false);

const currentViewHint = computed(() => {
  if (currentView.value === "groups") {
    return "Bygg arbetsgrupper genom att dra elever till rätt grupp och justera grupperna efter behov.";
  }
  return "Dra elever till platser och klicka på en elev när du vill öppna elevanteckningar.";
});

function selectStudent(studentId: string): void {
  selectedStudentId.value = studentId;
  if (currentView.value !== "seats") {
    isMetadataDrawerOpen.value = false;
    return;
  }
  isMetadataDrawerOpen.value = true;
}

async function reloadAfterConflict(): Promise<void> {
  await plannerState.reloadActiveWorkspace();
}

</script>

<template>
  <section class="space-y-6">
    <div
      v-if="plannerState.saveStatus === 'conflict'"
      class="system-message system-message-warning"
    >
      <div class="system-message-content">
        {{ plannerState.saveMessage }}
      </div>
      <button
        type="button"
        class="btn-ghost border-navy/30 bg-white shadow-none"
        @click="reloadAfterConflict"
      >
        Ladda om utkast
      </button>
    </div>

    <article class="space-y-4 border border-navy bg-white p-5 shadow-brutal-sm">
      <div class="flex flex-col gap-4 border-b border-navy/20 pb-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="space-y-1">
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Aktiv planering
          </p>
          <h2 class="font-serif text-3xl text-navy">
            {{ plannerState.roster?.name }}
          </h2>
          <p class="text-sm leading-relaxed text-navy/70">
            {{ plannerState.template?.name }} · revision {{ plannerState.draft?.revision ?? 0 }}
          </p>
        </div>

        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="btn-ghost"
            :class="currentView === 'groups' ? 'border-burgundy bg-white text-burgundy' : 'border-navy/30 bg-canvas shadow-none'"
            @click="
              currentView = 'groups';
              isMetadataDrawerOpen = false;
            "
          >
            Gruppvy
          </button>
          <button
            type="button"
            class="btn-ghost"
            :class="currentView === 'seats' ? 'border-burgundy bg-white text-burgundy' : 'border-navy/30 bg-canvas shadow-none'"
            @click="
              currentView = 'seats';
              isMetadataDrawerOpen = false;
            "
          >
            Sittplatser
          </button>
          <button
            type="button"
            class="btn-ghost border-navy/30 bg-canvas shadow-none"
            @click="emit('reset-selection')"
          >
            Byt klass / rum
          </button>
        </div>
      </div>

      <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-[minmax(0,1fr)_auto]">
        <div class="border border-navy/20 bg-canvas px-3 py-3 text-sm text-navy">
          <span class="font-semibold">Sparstatus:</span>
          {{ plannerState.saveStatus }}
          <span v-if="plannerState.saveMessage"> · {{ plannerState.saveMessage }}</span>
        </div>
        <div
          class="border border-navy/20 bg-canvas px-3 py-3 text-sm text-navy/70 xl:max-w-[26rem]"
        >
          {{ currentViewHint }}
        </div>
      </div>
    </article>

    <GroupBoard
      v-if="currentView === 'groups'"
      :selected-student-id="selectedStudentId"
      @student-selected="selectStudent"
    />
    <RoomCanvas
      v-else
      :selected-student-id="selectedStudentId"
      @student-selected="selectStudent"
    />

    <PlannerMetadataDrawer
      :selected-student-id="selectedStudentId"
      :open="isMetadataDrawerOpen"
      @close="isMetadataDrawerOpen = false"
    />
  </section>
</template>
