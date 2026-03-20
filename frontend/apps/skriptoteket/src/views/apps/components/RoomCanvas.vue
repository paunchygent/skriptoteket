<script setup lang="ts">
import { useClassroomState } from '../useClassroomState'
import SeatNode from './SeatNode.vue'
import { computed } from 'vue'

const state = useClassroomState()

const seats = computed(() => Object.values(state.seatsById))

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
    state.clearSeatAssignment(studentId)
  }
}

function onDragOver(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

// Ensure the canvas is large enough to contain all seats
const canvasStyle = computed(() => {
  let maxX = 800 // Default min width
  let maxY = 600 // Default min height

  for (const seat of seats.value) {
    if (seat.x + 100 > maxX) maxX = seat.x + 100
    if (seat.y + 100 > maxY) maxY = seat.y + 100
  }

  return {
    width: `${maxX}px`,
    height: `${maxY}px`
  }
})
</script>

<template>
  <div class="grid grid-cols-1 lg:grid-cols-4 gap-6 h-full">
    <!-- Student Pool (Unseated) -->
    <div
      class="lg:col-span-1 border-2 border-navy p-6 bg-white shadow-brutal-sm flex flex-col max-h-[calc(100vh-250px)]"
      @dragover="onDragOver"
      @drop="onDropToPool"
    >
      <div class="flex justify-between items-center mb-6 border-b-2 border-navy/10 pb-2">
        <h3 class="text-sm font-black uppercase tracking-widest text-navy">Ej placerade elever</h3>
        <span class="text-xs font-bold uppercase bg-navy text-white px-2 py-1 shadow-brutal-xs">{{ state.unseatedStudents.length }}</span>
      </div>

      <div class="flex flex-col gap-2 overflow-y-auto flex-grow p-1">
        <div
          v-for="student in state.unseatedStudents"
          :key="student.id"
          class="bg-white border-2 border-navy p-3 text-sm font-bold shadow-brutal-xs hover:bg-mint transition-colors cursor-grab active:cursor-grabbing flex justify-between items-center"
          draggable="true"
          @dragstart="onDragStart($event, student.id)"
        >
          <span>{{ student.display_name }}</span>
          <span
            v-if="state.groupAssignmentsByStudentId[student.id]"
            class="text-[10px] font-black uppercase text-navy/50 bg-navy/5 px-1.5 py-0.5 ml-2"
          >
            {{ state.groupsById[state.groupAssignmentsByStudentId[student.id]!]?.name }}
          </span>
        </div>

        <div
          v-if="state.unseatedStudents.length === 0"
          class="flex-grow flex items-center justify-center text-xs font-black uppercase tracking-widest text-navy/20 italic text-center p-8"
        >
          Alla elever är placerade
        </div>
      </div>
    </div>

    <!-- Room Canvas -->
    <div class="lg:col-span-3 border-2 border-navy bg-paper overflow-auto shadow-brutal-sm max-h-[calc(100vh-250px)] relative">
      <!-- Background Grid -->
      <div
        class="absolute inset-0 pointer-events-none opacity-20"
        style="background-image: linear-gradient(var(--huleedu-navy) 1px, transparent 1px), linear-gradient(90deg, var(--huleedu-navy) 1px, transparent 1px); background-size: 20px 20px;"
      />

      <!-- Canvas Area -->
      <div
        class="relative"
        :style="canvasStyle"
      >
        <SeatNode
          v-for="seat in seats"
          :key="seat.id"
          :seat="seat"
          :student="state.studentBySeatId[seat.id]"
          @student-dropped="state.assignStudentToSeat"
          @student-removed="state.clearSeatAssignment"
          @swap-requested="state.swapSeatAssignments"
        />
      </div>
    </div>
  </div>
</template>
