import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useClassroomState } from './useClassroomState'

describe('useClassroomState', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes from roster correctly', () => {
    const state = useClassroomState()
    const students = [
      { id: 's1', display_name: 'Student 1' },
      { id: 's2', display_name: 'Student 2' }
    ]

    state.initializeFromRoster(students)

    expect(Object.keys(state.studentsById)).toHaveLength(2)
    expect(state.studentsById['s1']).toEqual(students[0])
    expect(state.ungroupedStudents).toHaveLength(2)
  })

  it('assigns student to group', () => {
    const state = useClassroomState()
    const students = [{ id: 's1', display_name: 'S1' }]
    state.initializeFromRoster(students)
    state.initializeGroups(2)

    state.assignStudentToGroup('s1', 'group-1')

    expect(state.groupAssignmentsByStudentId['s1']).toBe('group-1')
    expect(state.ungroupedStudents).toHaveLength(0)
    expect(state.studentsByGroupId['group-1']).toHaveLength(1)
    expect(state.studentsByGroupId['group-1'][0].id).toBe('s1')
  })

  it('removes student from group', () => {
    const state = useClassroomState()
    const students = [{ id: 's1', display_name: 'S1' }]
    state.initializeFromRoster(students)
    state.initializeGroups(1)
    state.assignStudentToGroup('s1', 'group-1')

    state.removeStudentFromGroup('s1')

    expect(state.groupAssignmentsByStudentId['s1']).toBeNull()
    expect(state.ungroupedStudents).toHaveLength(1)
    expect(state.studentsByGroupId['group-1']).toHaveLength(0)
  })

  it('assigns student to seat and clears previous student', () => {
    const state = useClassroomState()
    const students = [
      { id: 's1', display_name: 'S1' },
      { id: 's2', display_name: 'S2' }
    ]
    const seats = [
      { id: 'seat-1', x: 0, y: 0 }
    ]
    state.initializeFromRoster(students)
    state.initializeFromTemplate(seats)

    // s1 takes seat-1
    state.assignStudentToSeat('s1', 'seat-1')
    expect(state.seatAssignmentsByStudentId['s1']).toBe('seat-1')

    // s2 takes seat-1, s1 should be cleared
    state.assignStudentToSeat('s2', 'seat-1')
    expect(state.seatAssignmentsByStudentId['s2']).toBe('seat-1')
    expect(state.seatAssignmentsByStudentId['s1']).toBeNull()
  })

  it('swaps seat assignments between students', () => {
    const state = useClassroomState()
    const students = [
      { id: 's1', display_name: 'S1' },
      { id: 's2', display_name: 'S2' }
    ]
    state.initializeFromRoster(students)

    state.seatAssignmentsByStudentId['s1'] = 'seat-1'
    state.seatAssignmentsByStudentId['s2'] = 'seat-2'

    state.swapSeatAssignments('s1', 's2')

    expect(state.seatAssignmentsByStudentId['s1']).toBe('seat-2')
    expect(state.seatAssignmentsByStudentId['s2']).toBe('seat-1')
  })
})
