<script setup lang="ts">
import { type Seat, type Student } from '../useClassroomState'

interface Props {
  seat: Seat
  student: Student | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'student-dropped', studentId: string, seatId: string): void
  (e: 'student-removed', studentId: string): void
  (e: 'swap-requested', studentIdA: string, studentIdB: string): void
}>()

function onDrop(event: DragEvent) {
  event.preventDefault()
  const sourceStudentId = event.dataTransfer?.getData('studentId')

  if (!sourceStudentId) return

  // If the seat is occupied by another student, it's a swap
  if (props.student && props.student.id !== sourceStudentId) {
    emit('swap-requested', sourceStudentId, props.student.id)
  } else {
    emit('student-dropped', sourceStudentId, props.seat.id)
  }
}

function onDragOver(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

function onDragStart(event: DragEvent) {
  if (event.dataTransfer && props.student) {
    event.dataTransfer.setData('studentId', props.student.id)
    event.dataTransfer.effectAllowed = 'move'
  }
}
</script>

<template>
  <div
    class="seat-node absolute border-2 border-navy shadow-brutal-sm flex items-center justify-center transition-all bg-white"
    :class="[
      student ? 'cursor-grab active:cursor-grabbing hover:bg-mint' : 'bg-paper border-dashed border-navy/30'
    ]"
    :style="{
      left: `${seat.x}px`,
      top: `${seat.y}px`,
      width: '80px',
      height: '80px'
    }"
    :draggable="!!student"
    @dragover="onDragOver"
    @drop="onDrop"
    @dragstart="onDragStart"
  >
    <div
      v-if="student"
      class="flex flex-col items-center p-1 w-full h-full justify-center relative"
    >
      <span class="text-xs font-bold text-center leading-tight truncate w-full px-1">
        {{ student.display_name }}
      </span>
      <button
        class="absolute -top-2 -right-2 bg-white border-2 border-navy text-navy hover:text-burgundy hover:border-burgundy w-5 h-5 rounded-full flex items-center justify-center font-black leading-none text-xs shadow-none cursor-pointer z-10 transition-colors"
        title="Ta bort från plats"
        @click.stop="emit('student-removed', student.id)"
      >
        &times;
      </button>
    </div>
    <div
      v-else
      class="text-[10px] font-black uppercase text-navy/20"
    >
      {{ seat.id }}
    </div>
  </div>
</template>
