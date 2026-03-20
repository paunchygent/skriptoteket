<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useClassroomState, type Student, type Seat, type PlanDraft } from './useClassroomState'
import GroupBoard from './components/GroupBoard.vue'
import RoomCanvas from './components/RoomCanvas.vue'
import CreateRosterModal from './components/CreateRosterModal.vue'
import CreateRoomTemplateModal from './components/CreateRoomTemplateModal.vue'
import { apiGet } from '../../api/client'

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

interface BootstrapResponse {
  lesson_modes: LessonMode[]
  feature_flags: Record<string, boolean>
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

// Modal State
const isCreateRosterModalOpen = ref(false)
const isCreateRoomModalOpen = ref(false)

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
    const [rosters, templates] = await Promise.all([
      apiGet<Roster[]>('/api/v1/apps/classroom.group-seating-studio/rosters'),
      apiGet<RoomTemplate[]>('/api/v1/apps/classroom.group-seating-studio/templates')
    ])
    availableRosters.value = rosters
    availableTemplates.value = templates
  } catch {
    // Silently fail, user can still see empty lists
  } finally {
    isLoadingCatalog.value = false
  }
}

onMounted(async () => {
  try {
    const data = await apiGet<BootstrapResponse>('/api/v1/apps/classroom.group-seating-studio/bootstrap')
    lessonModes.value = data.lesson_modes || [
      { id: 'seating', name: 'Sittplatsschema' },
      { id: 'group_work', name: 'Gruppering' }
    ]
    await fetchCatalog()

    // Check for existing draft to resume
    const savedDraftId = sessionStorage.getItem('classroom_planner_active_draft_id')
    if (savedDraftId) {
      await resumeDraft(savedDraftId)
    }
  } catch {
    bootstrapError.value = "Failed to load Klassrumskartan metadata."
  } finally {
    isBootstrapping.value = false
  }
})

async function resumeDraft(draftId: string) {
  try {
    const draft = await apiGet<PlanDraft>(`/api/v1/apps/classroom.group-seating-studio/drafts/${draftId}`)

    // Find associated roster and template
    const roster = availableRosters.value.find(r => r.id === draft.roster_id)
    const template = availableTemplates.value.find(t => t.id === draft.template_id)
    const mode = lessonModes.value.find(m => m.id === draft.lesson_mode_id)

    if (roster && template && mode) {
      selectedRoster.value = roster
      selectedTemplate.value = template
      selectedLessonMode.value = mode

      classroomState.initializeFromRoster(roster.students)
      classroomState.initializeFromTemplate(template.seats)
      classroomState.hydrate(draft)

      isReadyToStart.value = true
    }
  } catch (e) {
    console.error("Failed to resume draft", e)
    sessionStorage.removeItem('classroom_planner_active_draft_id')
  }
}

function onRosterCreated(newRoster: Roster) {
  isCreateRosterModalOpen.value = false
  availableRosters.value.push(newRoster)
  selectedRoster.value = newRoster
}

function onRoomCreated(newRoom: RoomTemplate) {
  isCreateRoomModalOpen.value = false
  availableTemplates.value.push(newRoom)
  selectedTemplate.value = newRoom
}

const isReadyToStart = ref(false)

async function startPlanning() {
  if (selectedLessonMode.value && selectedRoster.value && selectedTemplate.value) {
    classroomState.initializeFromRoster(selectedRoster.value.students)
    classroomState.initializeFromTemplate(selectedTemplate.value.seats)

    // Create the persistent draft
    await classroomState.createDraft(
      selectedRoster.value.id,
      selectedTemplate.value.id,
      selectedLessonMode.value.id
    )

    isReadyToStart.value = true
    currentView.value = 'groups'
  }
}

function resetSelection() {
  isReadyToStart.value = false
  sessionStorage.removeItem('classroom_planner_active_draft_id')
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
          class="px-4 py-2 border-2 border-navy bg-white text-navy font-black uppercase text-[10px] tracking-widest shadow-brutal-xs transition-all hover:bg-navy/5"
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
              class="px-8 py-4 border-2 border-navy transition-colors font-black uppercase tracking-widest text-sm"
              :class="selectedLessonMode?.id === mode.id ? 'bg-navy text-white shadow-none' : 'bg-white text-navy shadow-brutal hover:bg-navy/5'"
              @click="selectedLessonMode = mode"
            >
              {{ mode.name }}
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-12">
          <!-- Roster Selection -->
          <div class="space-y-6">
            <div class="flex justify-between items-end border-b-2 border-navy/10 pb-2">
              <h2 class="text-xl font-black text-navy uppercase tracking-widest">
                2. Välj Klasslista
              </h2>
              <button
                class="text-xs font-bold uppercase text-navy/60 hover:text-navy transition-colors underline decoration-2 underline-offset-4"
                @click="isCreateRosterModalOpen = true"
              >
                Skapa ny
              </button>
            </div>
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
                class="p-5 border-2 border-navy text-left transition-colors font-black uppercase tracking-widest text-xs"
                :class="selectedRoster?.id === roster.id ? 'bg-mint text-navy shadow-none' : 'bg-white shadow-brutal-xs hover:bg-paper'"
                @click="selectedRoster = roster"
              >
                {{ roster.name }}
                <span class="block text-[10px] opacity-60 mt-1 font-bold">{{ roster.students.length }} elever</span>
              </button>
            </div>
          </div>

          <!-- Room Template Selection -->
          <div class="space-y-6">
            <div class="flex justify-between items-end border-b-2 border-navy/10 pb-2">
              <h2 class="text-xl font-black text-navy uppercase tracking-widest">
                3. Välj Klassrum
              </h2>
              <button
                class="text-xs font-bold uppercase text-navy/60 hover:text-navy transition-colors underline decoration-2 underline-offset-4"
                @click="isCreateRoomModalOpen = true"
              >
                Skapa nytt
              </button>
            </div>
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
                class="p-5 border-2 border-navy text-left transition-colors font-black uppercase tracking-widest text-xs"
                :class="selectedTemplate?.id === tmpl.id ? 'bg-mint text-navy shadow-none' : 'bg-white shadow-brutal-xs hover:bg-paper'"
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
            class="px-16 py-8 border-4 border-navy font-black text-2xl uppercase transition-colors tracking-widest"
            :class="(selectedLessonMode && selectedRoster && selectedTemplate) ? 'bg-burgundy text-white shadow-brutal hover:bg-burgundy/90' : 'bg-navy/10 text-navy/20 cursor-not-allowed'"
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

          <div class="flex items-center gap-6">
            <!-- Group Count Control (only in grouping view) -->
            <div
              v-if="currentView === 'groups'"
              class="flex items-center gap-3 bg-paper border-2 border-navy p-1 px-3"
            >
              <span class="text-[10px] font-black uppercase tracking-widest text-navy/60">Antal grupper</span>
              <div class="flex items-center gap-2">
                <button
                  class="w-6 h-6 border border-navy flex items-center justify-center font-black hover:bg-navy hover:text-white transition-colors"
                  @click="classroomState.setGroupCount(classroomState.groupCount - 1)"
                >
                  -
                </button>
                <span class="text-sm font-bold w-4 text-center">{{ classroomState.groupCount }}</span>
                <button
                  class="w-6 h-6 border border-navy flex items-center justify-center font-black hover:bg-navy hover:text-white transition-colors"
                  @click="classroomState.setGroupCount(classroomState.groupCount + 1)"
                >
                  +
                </button>
              </div>
            </div>

            <div
              class="px-6 py-3 border-2 border-navy bg-white text-xs tracking-widest shadow-brutal-xs flex items-center gap-2"
              :class="{
                'text-navy/50': classroomState.saveStatus === 'idle',
                'text-blue-600 font-bold': classroomState.saveStatus === 'saving',
                'text-mint-800 font-bold': classroomState.saveStatus === 'saved',
                'text-burgundy font-black': classroomState.saveStatus === 'error'
              }"
            >
              <span
                v-if="classroomState.saveStatus === 'idle'"
                class="uppercase"
              >Utkast startat</span>
              <span
                v-else-if="classroomState.saveStatus === 'saving'"
                class="uppercase animate-pulse"
              >Sparar...</span>
              <span
                v-else-if="classroomState.saveStatus === 'saved'"
                class="uppercase"
              >Sparat ✔</span>
              <span
                v-else-if="classroomState.saveStatus === 'error'"
                class="uppercase"
              >Misslyckades att spara!</span>
            </div>
          </div>
        </div>

        <!-- Main Workspace -->
        <div class="min-h-[600px]">
          <GroupBoard v-show="currentView === 'groups'" />
          <RoomCanvas v-show="currentView === 'seats'" />
        </div>
      </div>
    </div>

    <!-- Modals -->
    <CreateRosterModal
      v-if="isCreateRosterModalOpen"
      @close="isCreateRosterModalOpen = false"
      @created="onRosterCreated"
    />

    <CreateRoomTemplateModal
      v-if="isCreateRoomModalOpen"
      @close="isCreateRoomModalOpen = false"
      @created="onRoomCreated"
    />
  </div>
</template>
