<script setup lang="ts">
/**
 * Planner workspace shell.
 *
 * This component renders the live Slice 2 classroom-planning workspace after a
 * draft has been created or resumed. It owns view switching, responsive
 * metadata-drawer state, and planning-profile toggles while delegating the
 * actual boards/canvas and suggestion engine UI to dedicated child components.
 */

import { computed, ref } from "vue";

import GroupBoard from "./GroupBoard.vue";
import PlannerMetadataDrawer from "./PlannerMetadataDrawer.vue";
import PlannerSuggestionsPanel from "./PlannerSuggestionsPanel.vue";
import RoomCanvas from "./RoomCanvas.vue";
import type { PlanningProfile } from "../classroomPlannerTypes";
import { useClassroomState } from "../useClassroomState";

type PlannerView = "groups" | "seats";

defineProps<{
  selectedLessonModeName: string;
}>();

const emit = defineEmits<{
  (e: "reset-selection"): void;
}>();

const plannerState = useClassroomState();

const currentView = ref<PlannerView>("groups");
const selectedStudentId = ref<string | null>(null);
const isMetadataDrawerOpen = ref(false);

const plannerProfile = computed<PlanningProfile>(() => plannerState.planningProfile);

function selectStudent(studentId: string): void {
  selectedStudentId.value = studentId;
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

    <div class="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(22rem,0.95fr)]">
      <div class="space-y-6">
        <article class="space-y-4 border border-navy bg-white p-5 shadow-brutal-sm">
          <div class="flex flex-col gap-4 border-b border-navy/20 pb-4 lg:flex-row lg:items-start lg:justify-between">
            <div class="space-y-1">
              <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                Aktiv planering
              </p>
              <h2 class="font-serif text-3xl text-navy">
                {{ plannerState.roster?.name }} · {{ selectedLessonModeName }}
              </h2>
              <p class="text-sm leading-relaxed text-navy/70">
                {{ plannerState.template?.name }} · revision {{ plannerState.draft?.revision ?? 0 }}
              </p>
            </div>

            <div class="flex flex-wrap gap-2">
              <button
                type="button"
                class="btn-ghost border-navy/30 bg-canvas shadow-none lg:hidden"
                @click="isMetadataDrawerOpen = true"
              >
                Elevmetadata
              </button>
              <button
                type="button"
                class="btn-ghost"
                :class="currentView === 'groups' ? 'border-burgundy bg-white text-burgundy' : 'border-navy/30 bg-canvas shadow-none'"
                @click="currentView = 'groups'"
              >
                Gruppvy
              </button>
              <button
                type="button"
                class="btn-ghost"
                :class="currentView === 'seats' ? 'border-burgundy bg-white text-burgundy' : 'border-navy/30 bg-canvas shadow-none'"
                @click="currentView = 'seats'"
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

          <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <label class="flex items-center justify-between gap-3 border border-navy/20 bg-canvas px-3 py-3 text-sm text-navy">
              <span>Elevmetadata i regelmotor</span>
              <input
                :checked="plannerProfile.enable_student_meta"
                type="checkbox"
                class="h-4 w-4"
                @change="plannerState.updatePlanningProfile({ enable_student_meta: ($event.target as HTMLInputElement).checked })"
              >
            </label>
            <label class="flex items-center justify-between gap-3 border border-navy/20 bg-canvas px-3 py-3 text-sm text-navy">
              <span>Parregler</span>
              <input
                :checked="plannerProfile.enable_pair_constraints"
                type="checkbox"
                class="h-4 w-4"
                @change="plannerState.updatePlanningProfile({ enable_pair_constraints: ($event.target as HTMLInputElement).checked })"
              >
            </label>
            <label class="flex items-center justify-between gap-3 border border-navy/20 bg-canvas px-3 py-3 text-sm text-navy">
              <span>Zonpreferenser</span>
              <input
                :checked="plannerProfile.enable_zone_preferences"
                type="checkbox"
                class="h-4 w-4"
                @change="plannerState.updatePlanningProfile({ enable_zone_preferences: ($event.target as HTMLInputElement).checked })"
              >
            </label>
            <label class="flex items-center justify-between gap-3 border border-navy/20 bg-canvas px-3 py-3 text-sm text-navy">
              <span>Historikregler</span>
              <input
                :checked="plannerProfile.enable_history_rules"
                type="checkbox"
                class="h-4 w-4"
                @change="plannerState.updatePlanningProfile({ enable_history_rules: ($event.target as HTMLInputElement).checked })"
              >
            </label>
            <label class="space-y-1 border border-navy/20 bg-canvas px-3 py-3 text-sm text-navy md:col-span-2 xl:col-span-1">
              <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                Profil
              </span>
              <select
                :value="plannerProfile.profile_kind"
                class="w-full border border-navy/30 bg-white px-3 py-2 text-sm text-navy"
                @change="plannerState.updatePlanningProfile({ profile_kind: ($event.target as HTMLSelectElement).value as PlanningProfile['profile_kind'] })"
              >
                <option value="focus_first">
                  Fokus först
                </option>
                <option value="balance_first">
                  Balans först
                </option>
                <option value="rotation_first">
                  Rotation först
                </option>
              </select>
            </label>
          </div>

          <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <label class="space-y-1">
              <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">Lärarnärhet</span>
              <input
                :value="plannerProfile.teacher_proximity_weight"
                type="range"
                min="1"
                max="3"
                step="1"
                class="w-full"
                @input="plannerState.updatePlanningProfile({ teacher_proximity_weight: Number(($event.target as HTMLInputElement).value) })"
              >
            </label>
            <label class="space-y-1">
              <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">Fokusstöd</span>
              <input
                :value="plannerProfile.focus_support_weight"
                type="range"
                min="1"
                max="3"
                step="1"
                class="w-full"
                @input="plannerState.updatePlanningProfile({ focus_support_weight: Number(($event.target as HTMLInputElement).value) })"
              >
            </label>
            <label class="space-y-1">
              <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">Stabilitet</span>
              <input
                :value="plannerProfile.stability_weight"
                type="range"
                min="1"
                max="3"
                step="1"
                class="w-full"
                @input="plannerState.updatePlanningProfile({ stability_weight: Number(($event.target as HTMLInputElement).value) })"
              >
            </label>
            <label class="space-y-1">
              <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">Balans</span>
              <input
                :value="plannerProfile.balance_weight"
                type="range"
                min="1"
                max="3"
                step="1"
                class="w-full"
                @input="plannerState.updatePlanningProfile({ balance_weight: Number(($event.target as HTMLInputElement).value) })"
              >
            </label>
            <label class="space-y-1">
              <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">Rotation</span>
              <input
                :value="plannerProfile.rotation_weight"
                type="range"
                min="1"
                max="3"
                step="1"
                class="w-full"
                @input="plannerState.updatePlanningProfile({ rotation_weight: Number(($event.target as HTMLInputElement).value) })"
              >
            </label>
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
      </div>

      <div class="space-y-6">
        <PlannerMetadataDrawer
          :selected-student-id="selectedStudentId"
          :open="isMetadataDrawerOpen"
          @close="isMetadataDrawerOpen = false"
        />
        <PlannerSuggestionsPanel />
      </div>
    </div>
  </section>
</template>
