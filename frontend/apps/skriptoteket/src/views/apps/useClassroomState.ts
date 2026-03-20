import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useClassroomState = defineStore('classroom-state', () => {
  // 1. Normalized Draft Entities
  // Mapped strictly by IDs rather than nested arrays to prevent destructive DND behavior.
  const studentsById = ref<Record<string, unknown>>({})
  const groupsById = ref<Record<string, unknown>>({})
  const seatsById = ref<Record<string, unknown>>({})

  // 2. Separate Assignment Axes
  // Null value implies unassigned for that specific axis.
  const groupAssignmentsByStudentId = ref<Record<string, string | null>>({})
  const seatAssignmentsByStudentId = ref<Record<string, string | null>>({})

  // 3. Strict State Reducers (to be implemented)
  // Drag-and-drop components MUST dispatch these instead of mutating arrays.

  function assignStudentToGroup(_studentId: string, _groupId: string) {
    throw new Error("Not implemented yet. Required by ST-23-05.")
  }

  function removeStudentFromGroup(_studentId: string) {
    throw new Error("Not implemented yet. Required by ST-23-05.")
  }

  function assignStudentToSeat(_studentId: string, _seatId: string) {
    throw new Error("Not implemented yet. Required by ST-23-05.")
  }

  function swapSeatAssignments(_seatIdA: string, _seatIdB: string) {
    throw new Error("Not implemented yet. Required by ST-23-05.")
  }

  function clearSeatAssignment(_studentId: string) {
    throw new Error("Not implemented yet. Required by ST-23-05.")
  }

  return {
    // State
    studentsById,
    groupsById,
    seatsById,
    groupAssignmentsByStudentId,
    seatAssignmentsByStudentId,

    // Reducers
    assignStudentToGroup,
    removeStudentFromGroup,
    assignStudentToSeat,
    swapSeatAssignments,
    clearSeatAssignment
  }
})
