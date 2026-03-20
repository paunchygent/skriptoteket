<script setup lang="ts">
import { useClassroomState } from '../useClassroomState'
import GroupCard from './GroupCard.vue'
import { computed } from 'vue'

const state = useClassroomState()

const groups = computed(() => Object.values(state.groupsById))

function onDragStart(event: DragEvent, studentId: string) {
  if (event.dataTransfer) {
    event.dataTransfer.setData('studentId', studentId)
    event.dataTransfer.effectAllowed = 'move'
  }
}

function onDropToPool(event: DragEvent) {
  event.preventDefault()
  const studentId = event.dataTransfer?.getData('studentId')
  if (studentId) {
    state.removeStudentFromGroup(studentId)
  }
}

function onDragOver(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}
</script>

<template>
  <div class="grid grid-cols-1 lg:grid-cols-4 gap-6 h-full">
    <!-- Student Pool -->
    <div
      class="lg:col-span-1 border-2 border-navy p-6 bg-white shadow-brutal-sm flex flex-col max-h-[calc(100vh-250px)]"
      @dragover="onDragOver"
      @drop="onDropToPool"
    >
      <div class="flex justify-between items-center mb-6 border-b-2 border-navy/10 pb-2">
        <h3 class="text-sm font-black uppercase tracking-widest text-navy">Ej i grupp</h3>
        <span class="text-xs font-bold uppercase bg-navy text-white px-2 py-1 shadow-brutal-xs">{{ state.ungroupedStudents.length }}</span>
      </div>

      <div class="flex flex-col gap-2 overflow-y-auto flex-grow p-1">
        <div
          v-for="student in state.ungroupedStudents"
          :key="student.id"
          class="bg-white border-2 border-navy p-3 text-sm font-bold shadow-brutal-xs hover:bg-mint hover:-translate-y-0.5 transition-all cursor-grab active:cursor-grabbing flex justify-between items-center"
          draggable="true"
          @dragstart="onDragStart($event, student.id)"
        >
          <span>{{ student.display_name }}</span>
          <span
            v-if="state.seatAssignmentsByStudentId[student.id]"
            class="text-[10px] font-black uppercase text-navy/50 bg-navy/5 px-1.5 py-0.5 ml-2"
            title="Placerad"
          >
            Stol {{ state.seatAssignmentsByStudentId[student.id] }}
          </span>
        </div>

        <div
          v-if="state.ungroupedStudents.length === 0"
          class="flex-grow flex items-center justify-center text-xs font-black uppercase tracking-widest text-navy/20 italic text-center p-8"
        >
          Alla elever är i grupp
        </div>
      </div>
    </div>

    <!-- Groups Grid -->
    <div class="lg:col-span-3 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6 overflow-y-auto pr-4 max-h-[calc(100vh-250px)] p-1">
      <GroupCard
        v-for="group in groups"
        :key="group.id"
        :group="group"
        :students="state.studentsByGroupId[group.id] || []"
        @student-dropped="state.assignStudentToGroup"
        @student-removed="state.removeStudentFromGroup"
      />
    </div>
  </div>
</template>
