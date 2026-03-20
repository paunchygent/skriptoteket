import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Student {
  id: string
  display_name: string
}

export interface Group {
  id: string
  name: string
}

export interface Seat {
  id: string
  x: number
  y: number
  zone?: string | null
}

export const useClassroomState = defineStore('classroom-state', () => {
  // 1. Normalized Draft Entities
  const studentsById = ref<Record<string, Student>>({})
  const groupsById = ref<Record<string, Group>>({})
  const seatsById = ref<Record<string, Seat>>({})

  // 2. Separate Assignment Axes
  // studentId -> groupId
  const groupAssignmentsByStudentId = ref<Record<string, string | null>>({})
  // studentId -> seatId
  const seatAssignmentsByStudentId = ref<Record<string, string | null>>({})

  // Persistence State
  const activeDraftId = ref<string | null>(null)
  const saveStatus = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
  let saveTimeout: ReturnType<typeof setTimeout> | null = null

  // 3. Getters
  const ungroupedStudents = computed(() => {
    return Object.values(studentsById.value).filter(
      s => !groupAssignmentsByStudentId.value[s.id]
    )
  })

  const unseatedStudents = computed(() => {
    return Object.values(studentsById.value).filter(
      s => !seatAssignmentsByStudentId.value[s.id]
    )
  })

  const studentsByGroupId = computed(() => {
    const map: Record<string, Student[]> = {}
    Object.keys(groupsById.value).forEach(groupId => {
      map[groupId] = []
    })

    Object.entries(groupAssignmentsByStudentId.value).forEach(([studentId, groupId]) => {
      if (groupId && map[groupId] && studentsById.value[studentId]) {
        map[groupId].push(studentsById.value[studentId])
      }
    })
    return map
  })

  const studentBySeatId = computed(() => {
    const map: Record<string, Student | null> = {}
    Object.keys(seatsById.value).forEach(seatId => {
      map[seatId] = null
    })

    Object.entries(seatAssignmentsByStudentId.value).forEach(([studentId, seatId]) => {
      if (seatId && studentsById.value[studentId]) {
        map[seatId] = studentsById.value[studentId]
      }
    })
    return map
  })

  // 4. Initialization

  function initializeFromRoster(students: Student[]) {
    studentsById.value = {}
    groupAssignmentsByStudentId.value = {}
    seatAssignmentsByStudentId.value = {}

    students.forEach(s => {
      studentsById.value[s.id] = s
      groupAssignmentsByStudentId.value[s.id] = null
      seatAssignmentsByStudentId.value[s.id] = null
    })
  }

  function initializeGroups(count: number) {
    groupsById.value = {}
    for (let i = 1; i <= count; i++) {
      const id = `group-${i}`
      groupsById.value[id] = { id, name: `Grupp ${i}` }
    }
  }

  function initializeFromTemplate(seats: Seat[]) {
    seatsById.value = {}
    seats.forEach(s => {
      seatsById.value[s.id] = s
    })
  }

  // 5. Draft Persistence API

  async function createDraft(rosterId: string, templateId: string, lessonModeId: string) {
    saveStatus.value = 'saving'
    try {
      const response = await fetch('/api/v1/apps/classroom.group-seating-studio/drafts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          roster_id: rosterId,
          template_id: templateId,
          lesson_mode_id: lessonModeId,
          group_assignments: groupAssignmentsByStudentId.value,
          seat_assignments: seatAssignmentsByStudentId.value
        })
      })
      if (!response.ok) throw new Error('Failed to create draft')
      const data = await response.json()
      activeDraftId.value = data.id
      saveStatus.value = 'saved'
    } catch (e) {
      saveStatus.value = 'error'
      console.error(e)
    }
  }

  function _triggerAutosave() {
    if (!activeDraftId.value) return

    saveStatus.value = 'saving'
    if (saveTimeout) clearTimeout(saveTimeout)

    saveTimeout = setTimeout(async () => {
      try {
        const response = await fetch(`/api/v1/apps/classroom.group-seating-studio/drafts/${activeDraftId.value}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            group_assignments: groupAssignmentsByStudentId.value,
            seat_assignments: seatAssignmentsByStudentId.value
          })
        })
        if (!response.ok) throw new Error('Failed to save draft')
        saveStatus.value = 'saved'
      } catch (e) {
        saveStatus.value = 'error'
        console.error(e)
      }
    }, 1000) // 1 second debounce
  }

  // 6. Strict State Reducers

  function assignStudentToGroup(studentId: string, groupId: string) {
    if (!studentsById.value[studentId]) return
    if (!groupsById.value[groupId]) return

    groupAssignmentsByStudentId.value[studentId] = groupId
    _triggerAutosave()
  }

  function removeStudentFromGroup(studentId: string) {
    if (!studentsById.value[studentId]) return
    groupAssignmentsByStudentId.value[studentId] = null
    _triggerAutosave()
  }

  function assignStudentToSeat(studentId: string, seatId: string) {
    if (!studentsById.value[studentId]) return
    if (!seatsById.value[seatId]) return

    // Ensure seat is not already taken by another student
    Object.entries(seatAssignmentsByStudentId.value).forEach(([sid, targetSeatId]) => {
      if (targetSeatId === seatId) {
        seatAssignmentsByStudentId.value[sid] = null
      }
    })

    seatAssignmentsByStudentId.value[studentId] = seatId
    _triggerAutosave()
  }

  function swapSeatAssignments(studentIdA: string, studentIdB: string) {
    const seatA = seatAssignmentsByStudentId.value[studentIdA]
    const seatB = seatAssignmentsByStudentId.value[studentIdB]

    seatAssignmentsByStudentId.value[studentIdA] = seatB || null
    seatAssignmentsByStudentId.value[studentIdB] = seatA || null
    _triggerAutosave()
  }

  function clearSeatAssignment(studentId: string) {
    if (!studentsById.value[studentId]) return
    seatAssignmentsByStudentId.value[studentId] = null
    _triggerAutosave()
  }

  return {
    // State
    studentsById,
    groupsById,
    seatsById,
    groupAssignmentsByStudentId,
    seatAssignmentsByStudentId,
    activeDraftId,
    saveStatus,

    // Getters
    ungroupedStudents,
    unseatedStudents,
    studentsByGroupId,
    studentBySeatId,

    // Actions
    initializeFromRoster,
    initializeGroups,
    initializeFromTemplate,
    createDraft,
    assignStudentToGroup,
    removeStudentFromGroup,
    assignStudentToSeat,
    swapSeatAssignments,
    clearSeatAssignment
  }
})
