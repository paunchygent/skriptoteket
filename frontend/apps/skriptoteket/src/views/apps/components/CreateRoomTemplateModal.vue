<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Seat, RoomTemplate } from '../useClassroomState'

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created', template: RoomTemplate): void
}>()

const name = ref('')
const isSubmitting = ref(false)
const error = ref<string | null>(null)

// 10x10 Grid representation for building a room
const GRID_SIZE = 10
const SEAT_SIZE = 80 // pixels
const grid = ref<boolean[][]>(
  Array.from({ length: GRID_SIZE }, () => Array(GRID_SIZE).fill(false))
)

function toggleSeat(row: number, col: number) {
  grid.value[row][col] = !grid.value[row][col]
}

const parsedSeats = computed<Seat[]>(() => {
  const seats: Seat[] = []
  let seatCounter = 1

  for (let row = 0; row < GRID_SIZE; row++) {
    for (let col = 0; col < GRID_SIZE; col++) {
      if (grid.value[row][col]) {
        seats.push({
          id: `seat-${seatCounter++}`,
          x: col * SEAT_SIZE,
          y: row * SEAT_SIZE
        })
      }
    }
  }
  return seats
})

const isValid = computed(() => {
  return name.value.trim().length > 0 && parsedSeats.value.length > 0
})

async function submit() {
  if (!isValid.value) return

  isSubmitting.value = true
  error.value = null

  try {
    const response = await fetch('/api/v1/apps/classroom.group-seating-studio/templates', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: name.value.trim(),
        seats: parsedSeats.value
      })
    })

    if (!response.ok) {
      throw new Error('Kunde inte spara klassrummet.')
    }

    const data = await response.json()
    emit('created', data)
  } catch (e: unknown) {
    if (e instanceof Error) {
      error.value = e.message
    } else {
      error.value = 'Ett okänt fel uppstod.'
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-navy/80 backdrop-blur-sm p-4 overflow-y-auto">
    <div class="bg-white border-4 border-navy shadow-[16px_16px_0_0_rgba(15,23,42,1)] max-w-2xl w-full p-8 relative my-auto">
      <button
        class="absolute top-4 right-4 text-navy/50 hover:text-navy font-black text-2xl leading-none"
        @click="emit('close')"
      >
        &times;
      </button>

      <h2 class="text-2xl font-black uppercase tracking-widest text-navy mb-6 border-b-4 border-navy/10 pb-2">
        Skapa Klassrum
      </h2>

      <div
        v-if="error"
        class="mb-6 p-4 border-2 border-burgundy bg-burgundy/10 text-burgundy font-bold text-sm"
      >
        {{ error }}
      </div>

      <div class="space-y-6">
        <div>
          <label class="block text-sm font-bold uppercase tracking-widest text-navy mb-2">Klassrummets namn</label>
          <input
            v-model="name"
            type="text"
            placeholder="T.ex. Sal 304"
            class="w-full border-2 border-navy p-3 text-lg font-bold placeholder:font-normal focus:outline-none focus:ring-4 focus:ring-navy/20"
          >
        </div>

        <div>
          <div class="flex justify-between items-end mb-2">
            <label class="block text-sm font-bold uppercase tracking-widest text-navy">Karta</label>
            <span class="text-xs font-bold text-navy/60">{{ parsedSeats.length }} platser utplacerade</span>
          </div>
          <p class="text-xs text-navy/60 mb-2">Klicka i rutnätet för att placera ut bord/stolar.</p>

          <div class="border-2 border-navy bg-paper p-4 flex justify-center overflow-x-auto">
            <div
              class="grid gap-1"
              :style="{ gridTemplateColumns: `repeat(${GRID_SIZE}, minmax(0, 1fr))` }"
            >
              <template
                v-for="row in GRID_SIZE"
                :key="`row-${row}`"
              >
                <div
                  v-for="col in GRID_SIZE"
                  :key="`cell-${row}-${col}`"
                  class="w-10 h-10 border-2 transition-colors cursor-pointer"
                  :class="grid[row-1][col-1] ? 'bg-navy border-navy' : 'bg-white border-navy/20 hover:border-navy/50'"
                  @click="toggleSeat(row-1, col-1)"
                />
              </template>
            </div>
          </div>
        </div>

        <div class="pt-4 flex justify-end gap-4 border-t-2 border-navy/10">
          <button
            type="button"
            class="px-6 py-3 font-bold uppercase tracking-widest text-navy hover:bg-navy/5 transition-colors"
            @click="emit('close')"
          >
            Avbryt
          </button>
          <button
            type="button"
            class="px-8 py-3 border-2 border-navy font-black uppercase tracking-widest transition-colors"
            :class="isValid && !isSubmitting ? 'bg-mint text-navy hover:bg-mint-400' : 'bg-navy/10 text-navy/30 cursor-not-allowed'"
            :disabled="!isValid || isSubmitting"
            @click="submit"
          >
            {{ isSubmitting ? 'Sparar...' : 'Spara Klassrum' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
