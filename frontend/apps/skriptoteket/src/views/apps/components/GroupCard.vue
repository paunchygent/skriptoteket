<script setup lang="ts">
import { useClassroomState, type Student, type Group } from '../useClassroomState'

interface Props {
  group: Group
  students: Student[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'student-dropped', studentId: string, groupId: string): void
  (e: 'student-removed', studentId: string): void
}>()

const state = useClassroomState()

function onDrop(event: DragEvent) {
  event.preventDefault()
  const studentId = event.dataTransfer?.getData('studentId')
  if (studentId) {
    emit('student-dropped', studentId, props.group.id)
  }
}

function onDragOver(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

function onDragStart(event: DragEvent, student: Student) {
  if (event.dataTransfer) {
    event.dataTransfer.setData('studentId', student.id)
    event.dataTransfer.effectAllowed = 'move'
  }
}
</script>

<template>
  <div
    class="border-2 border-navy p-4 bg-white shadow-brutal-sm flex flex-col min-h-[200px] transition-colors hover:bg-paper"
    @dragover="onDragOver"
    @drop="onDrop"
  >
    <div class="flex justify-between items-center mb-4 border-b-2 border-navy/10 pb-2">
      <h3 class="text-sm font-black uppercase tracking-widest text-navy">{{ group.name }}</h3>
      <span class="text-[10px] font-bold uppercase bg-navy text-white px-2 py-0.5 rounded">{{ students.length }}</span>
    </div>

    <div class="flex flex-col gap-2 flex-grow">
      <div
        v-for="student in students"
        :key="student.id"
        class="bg-white border-2 border-navy p-2 text-xs font-bold flex justify-between items-center cursor-grab active:cursor-grabbing hover:bg-mint transition-colors"
        draggable="true"
        @dragstart="onDragStart($event, student)"
      >
        <div class="flex flex-col">
          <span class="truncate">{{ student.display_name }}</span>
          <span
            v-if="state.seatAssignmentsByStudentId[student.id]"
            class="text-[9px] text-navy/50 uppercase tracking-widest font-black mt-0.5"
          >
            Stol {{ state.seatAssignmentsByStudentId[student.id] }}
          </span>
        </div>
        <button
          class="text-navy hover:text-burgundy transition-colors font-black text-lg leading-none shrink-0 ml-2"
          title="Ta bort från grupp"
          @click="emit('student-removed', student.id)"
        >
          &times;
        </button>
      </div>

      <div
        v-if="students.length === 0"
        class="flex-grow flex items-center justify-center text-[10px] font-bold uppercase tracking-widest text-navy/30 italic text-center p-4"
      >
        Släpp elever här
      </div>
    </div>
  </div>
</template>
