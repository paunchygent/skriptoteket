<script setup lang="ts">
import { ref, onMounted } from 'vue'
// import LessonModePicker from './LessonModePicker.vue'
// import GroupBoard from './GroupBoard.vue'
// import RoomCanvas from './RoomCanvas.vue'
// import RosterPane from './RosterPane.vue'
// import { useClassroomState } from './useClassroomState'

interface LessonMode {
  id: string
  name: string
}

const title = ref("Klassrumskartan")

// Bootstrapping State
const isBootstrapping = ref(true)
const bootstrapError = ref<string | null>(null)
const lessonModes = ref<LessonMode[]>([])
const selectedLessonMode = ref<LessonMode | null>(null)

onMounted(async () => {
  try {
    // Expected endpoint from ST-23-01
    const res = await fetch('/api/v1/apps/classroom.group-seating-studio/bootstrap')
    if (!res.ok) {
      // Fallback for UI building before the API is ready
      lessonModes.value = [{ id: 'standard', name: 'Standard Lektion' }]
    } else {
      const data = await res.json()
      lesson_modes.value = data.lesson_modes || []
      }
      } catch {
      bootstrapError.value = "Failed to load Klassrumskartan metadata."
      } finally {
    isBootstrapping.value = false
  }
})
</script>

<template>
  <div class="max-w-7xl mx-auto space-y-6">
    <div class="border-b-2 border-burgundy pb-4">
      <h1 class="text-3xl font-extrabold tracking-tight text-navy uppercase drop-shadow-sm">
        {{ title }}
      </h1>
    </div>

    <div
      v-if="isBootstrapping"
      class="p-12 text-center text-navy font-bold uppercase tracking-widest animate-pulse"
    >
      Laddar applikation...
    </div>

    <div
      v-else-if="bootstrapError"
      class="p-6 border-2 border-red-500 bg-red-50 text-red-700 font-bold shadow-brutal-sm"
    >
      {{ bootstrapError }}
    </div>

    <div v-else>
      <!-- Lesson Mode Gate (ST-23-02) -->
      <div
        v-if="!selectedLessonMode"
        class="border-2 border-navy border-dashed p-12 text-center bg-paper shadow-brutal-sm"
      >
        <h2 class="text-2xl font-black text-navy uppercase mb-6 tracking-widest">
          Välj Lektionsläge
        </h2>
        <div class="flex flex-wrap justify-center gap-4">
          <button
            v-for="mode in lessonModes"
            :key="mode.id"
            class="px-6 py-4 border-2 border-navy bg-white shadow-[4px_4px_0_0_rgba(15,23,42,1)] hover:-translate-y-1 hover:shadow-[6px_6px_0_0_rgba(15,23,42,1)] font-bold uppercase transition-all"
            @click="selectedLessonMode = mode"
          >
            {{ mode.name }}
          </button>
        </div>
      </div>

      <!-- Planner Canvas Workspace -->
      <div
        v-else
        class="grid grid-cols-1 lg:grid-cols-4 gap-6 opacity-50 pointer-events-none"
      >
        <!-- Simulated Roster Pane -->
        <div class="lg:col-span-1 border-2 border-navy p-4 min-h-[500px] bg-white shadow-brutal-sm flex flex-col items-center justify-center">
          <span class="text-navy/50 font-bold uppercase tracking-widest">Roster Pane (Pending)</span>
        </div>

        <!-- Simulated Boards -->
        <div class="lg:col-span-3 grid grid-rows-2 gap-6 relative">
          <div class="border-2 border-navy p-4 min-h-[300px] bg-paper shadow-brutal-sm flex items-center justify-center">
            <span class="text-navy/50 font-bold uppercase tracking-widest">Group Board (Pending)</span>
          </div>
          <div class="border-2 border-navy p-4 min-h-[300px] bg-paper shadow-brutal-sm flex items-center justify-center">
            <span class="text-navy/50 font-bold uppercase tracking-widest">Room Canvas (Pending)</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
