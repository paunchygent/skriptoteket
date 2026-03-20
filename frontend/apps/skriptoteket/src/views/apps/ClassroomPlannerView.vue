<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useClassroomState, type Student, type Seat } from './useClassroomState'
import GroupBoard from './components/GroupBoard.vue'
import RoomCanvas from './components/RoomCanvas.vue'

interface LessonMode {
  id: string
  name: string
}

interface Roster {
  id: string
  name: string
  students: Student[]
}

interface RoomTemplate {
  id: string
  name: string
  seats: Seat[]
}

const classroomState = useClassroomState()
const title = ref("Klassrumskartan")

// Bootstrapping State
const isBootstrapping = ref(true)
const bootstrapError = ref<string | null>(null)
const lessonModes = ref<LessonMode[]>([])

// Selection State
const selectedLessonMode = ref<LessonMode | null>(null)
const selectedRoster = ref<Roster | null>(null)
const selectedTemplate = ref<RoomTemplate | null>(null)

// View State
type PlannerView = 'groups' | 'seats'
const currentView = ref<PlannerView>('groups')

// Catalog State
const availableRosters = ref<Roster[]>([])
const availableTemplates = ref<RoomTemplate[]>([])
const isLoadingCatalog = ref(false)

async function fetchCatalog() {
  isLoadingCatalog.value = true
  try {
    const [rostersRes, templatesRes] = await Promise.all([
      fetch('/api/v1/apps/classroom.group-seating-studio/rosters'),
      fetch('/api/v1/apps/classroom.group-seating-studio/templates')
    ])

    if (rostersRes.ok) availableRosters.value = await rostersRes.json()
    if (templatesRes.ok) availableTemplates.value = await templatesRes.json()
  } catch {
    // Silently fail, user can still see empty lists
  } finally {
    isLoadingCatalog.value = false
  }
}

onMounted(async () => {
  try {
    const res = await fetch('/api/v1/apps/classroom.group-seating-studio/bootstrap')
    if (!res.ok) {
      lessonModes.value = [
        { id: 'standard', name: 'Standard Lektion' },
        { id: 'test', name: 'Prov/Examination' }
      ]
    } else {
      const data = await res.json()
      lessonModes.value = data.lesson_modes || []
    }
    await fetchCatalog()
  } catch {
    bootstrapError.value = "Failed to load Klassrumskartan metadata."
  } finally {
    isBootstrapping.value = false
  }
})

const isReadyToStart = ref(false)

function startPlanning() {
  if (selectedLessonMode.value && selectedRoster.value && selectedTemplate.value) {
    classroomState.initializeFromRoster(selectedRoster.value.students)
    classroomState.initializeFromTemplate(selectedTemplate.value.seats)
    classroomState.initializeGroups(6) // Default to 6 groups for now
    isReadyToStart.value = true
    currentView.value = 'groups'
  }
}

function resetSelection() {
  isReadyToStart.value = false
}
</script>

<template>
  <div class="max-w-7xl mx-auto space-y-6 px-4">
    <!-- Header -->
    <div class="border-b-4 border-navy pb-4 flex justify-between items-end">
      <div>
        <h1 class="text-3xl font-black tracking-tighter text-navy uppercase">
          {{ title }}
        </h1>
        <p
          v-if="isReadyToStart"
          class="text-xs font-bold uppercase tracking-widest text-navy/60 mt-1"
        >
          Planering: {{ selectedRoster?.name }} &middot; {{ selectedLessonMode?.name }}
        </p>
      </div>
      <div
        v-if="isReadyToStart"
        class="flex gap-4"
      >
        <button
          class="px-4 py-2 border-2 border-navy bg-white text-navy font-black uppercase text-[10px] tracking-widest shadow-brutal-xs hover:-translate-y-0.5 transition-all"
          @click="resetSelection"
        >
          Byt inställningar
        </button>
      </div>
    </div>

    <!-- Loading/Error -->
    <div
      v-if="isBootstrapping"
      class="p-12 text-center text-navy font-black uppercase tracking-widest animate-pulse"
    >
      Laddar applikation...
    </div>

    <div
      v-else-if="bootstrapError"
      class="p-6 border-4 border-burgundy bg-paper text-burgundy font-black shadow-brutal text-center uppercase"
    >
      {{ bootstrapError }}
    </div>

    <div v-else>
      <!-- 1. Selection Gate -->
      <div
        v-if="!isReadyToStart"
        class="border-4 border-navy p-10 bg-paper shadow-brutal space-y-10"
      >
        <div class="space-y-6">
          <h2 class="text-xl font-black text-navy uppercase tracking-widest border-b-2 border-navy/10 pb-2">
            1. Välj Lektionsläge
          </h2>
          <div class="flex flex-wrap gap-4">
            <button
              v-for="mode in lessonModes"
              :key="mode.id"
              class="px-8 py-4 border-2 border-navy transition-all font-black uppercase tracking-widest text-sm"
              :class="selectedLessonMode?.id === mode.id ? 'bg-navy text-white shadow-none translate-y-1' : 'bg-white text-navy shadow-brutal hover:-translate-y-1'"
              @click="selectedLessonMode = mode"
            >
              {{ mode.name }}
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-12">
          <!-- Roster Selection -->
          <div class="space-y-6">
            <h2 class="text-xl font-black text-navy uppercase tracking-widest border-b-2 border-navy/10 pb-2">
              2. Välj Klasslista
            </h2>
            <div
              v-if="isLoadingCatalog"
              class="animate-pulse text-navy/50 font-bold uppercase text-xs"
            >
              Söker i biblioteket...
            </div>
            <div
              v-else-if="availableRosters.length === 0"
              class="text-navy/40 font-bold italic py-4 border-2 border-dashed border-navy/20 text-center"
            >
              Inga sparade klasslistor hittades.
            </div>
            <div
              v-else
              class="flex flex-col gap-3 max-h-[300px] overflow-y-auto pr-2"
            >
              <button
                v-for="roster in availableRosters"
                :key="roster.id"
                class="p-5 border-2 border-navy text-left transition-all font-black uppercase tracking-widest text-xs"
                :class="selectedRoster?.id === roster.id ? 'bg-mint text-navy translate-x-1 shadow-none' : 'bg-white shadow-brutal-xs hover:bg-paper'"
                @click="selectedRoster = roster"
              >
                {{ roster.name }}
                <span class="block text-[10px] opacity-60 mt-1 font-bold">{{ roster.students.length }} elever</span>
              </button>
            </div>
          </div>

          <!-- Room Template Selection -->
          <div class="space-y-6">
            <h2 class="text-xl font-black text-navy uppercase tracking-widest border-b-2 border-navy/10 pb-2">
              3. Välj Klassrum
            </h2>
            <div
              v-if="isLoadingCatalog"
              class="animate-pulse text-navy/50 font-bold uppercase text-xs"
            >
              Söker i biblioteket...
            </div>
            <div
              v-else-if="availableTemplates.length === 0"
              class="text-navy/40 font-bold italic py-4 border-2 border-dashed border-navy/20 text-center"
            >
              Inga sparade klassrum hittades.
            </div>
            <div
              v-else
              class="flex flex-col gap-3 max-h-[300px] overflow-y-auto pr-2"
            >
              <button
                v-for="tmpl in availableTemplates"
                :key="tmpl.id"
                class="p-5 border-2 border-navy text-left transition-all font-black uppercase tracking-widest text-xs"
                :class="selectedTemplate?.id === tmpl.id ? 'bg-mint text-navy translate-x-1 shadow-none' : 'bg-white shadow-brutal-xs hover:bg-paper'"
                @click="selectedTemplate = tmpl"
              >
                {{ tmpl.name }}
                <span class="block text-[10px] opacity-60 mt-1 font-bold">{{ tmpl.seats.length }} platser</span>
              </button>
            </div>
          </div>
        </div>

        <div class="pt-10 border-t-2 border-navy/10 flex justify-center">
          <button
            class="px-16 py-8 border-4 border-navy font-black text-2xl uppercase transition-all tracking-widest"
            :class="(selectedLessonMode && selectedRoster && selectedTemplate) ? 'bg-burgundy text-white shadow-brutal hover:-translate-y-1 hover:shadow-[12px_12px_0_0_rgba(15,23,42,1)]' : 'bg-navy/10 text-navy/20 cursor-not-allowed'"
            :disabled="!(selectedLessonMode && selectedRoster && selectedTemplate)"
            @click="startPlanning"
          >
            Öppna Planeringsverktyget
          </button>
        </div>
      </div>

      <!-- 2. Planner Workspace -->
      <div
        v-else
        class="flex flex-col gap-6"
      >
        <!-- Toolbar -->
        <div class="flex justify-between items-center border-4 border-navy bg-white p-4 shadow-brutal-sm">
          <div class="flex gap-2 p-1 bg-paper border-2 border-navy">
            <button
              class="px-6 py-2 font-black uppercase text-xs tracking-widest transition-colors cursor-pointer"
              :class="currentView === 'groups' ? 'bg-navy text-white' : 'bg-white text-navy/60 hover:text-navy'"
              @click="currentView = 'groups'"
            >
              Gruppering
            </button>
            <button
              class="px-6 py-2 font-black uppercase text-xs tracking-widest transition-colors cursor-pointer"
              :class="currentView === 'seats' ? 'bg-navy text-white' : 'bg-white text-navy/60 hover:text-navy'"
              @click="currentView = 'seats'"
            >
              Placering
            </button>
          </div>

          <div class="flex gap-4">
            <button
              class="px-6 py-3 border-2 border-navy bg-white text-navy font-black uppercase text-xs tracking-widest shadow-brutal-xs hover:-translate-y-0.5 transition-all opacity-50 cursor-not-allowed"
              disabled
            >
              Spara utkast
            </button>
          </div>
        </div>

        <!-- Main Workspace -->
        <div class="min-h-[600px]">
          <GroupBoard v-show="currentView === 'groups'" />
          <RoomCanvas v-show="currentView === 'seats'" />
        </div>
      </div>
    </div>
  </div>
</template>
