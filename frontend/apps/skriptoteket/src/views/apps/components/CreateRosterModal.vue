<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Student, Roster } from '../useClassroomState'

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created', roster: Roster): void
}>()

const name = ref('')
const rawStudents = ref('')
const isSubmitting = ref(false)
const error = ref<string | null>(null)

const parsedStudents = computed<Student[]>(() => {
  return rawStudents.value
    .split('\n')
    .map(name => name.trim())
    .filter(name => name.length > 0)
    .map(name => ({
      id: crypto.randomUUID(),
      display_name: name
    }))
})

const isValid = computed(() => {
  return name.value.trim().length > 0 && parsedStudents.value.length > 0
})

async function submit() {
  if (!isValid.value) return

  isSubmitting.value = true
  error.value = null

  try {
    const response = await fetch('/api/v1/apps/classroom.group-seating-studio/rosters', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: name.value.trim(),
        students: parsedStudents.value
      })
    })

    if (!response.ok) {
      throw new Error('Kunde inte spara klasslistan.')
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
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-navy/80 backdrop-blur-sm p-4">
    <div class="bg-white border-4 border-navy shadow-[16px_16px_0_0_rgba(15,23,42,1)] max-w-lg w-full p-8 relative">
      <button
        class="absolute top-4 right-4 text-navy/50 hover:text-navy font-black text-2xl leading-none"
        @click="emit('close')"
      >
        &times;
      </button>

      <h2 class="text-2xl font-black uppercase tracking-widest text-navy mb-6 border-b-4 border-navy/10 pb-2">
        Skapa Klasslista
      </h2>

      <div
        v-if="error"
        class="mb-6 p-4 border-2 border-burgundy bg-burgundy/10 text-burgundy font-bold text-sm"
      >
        {{ error }}
      </div>

      <div class="space-y-6">
        <div>
          <label class="block text-sm font-bold uppercase tracking-widest text-navy mb-2">Klassens namn</label>
          <input
            v-model="name"
            type="text"
            placeholder="T.ex. Klass 9A"
            class="w-full border-2 border-navy p-3 text-lg font-bold placeholder:font-normal focus:outline-none focus:ring-4 focus:ring-navy/20"
          >
        </div>

        <div>
          <div class="flex justify-between items-end mb-2">
            <label class="block text-sm font-bold uppercase tracking-widest text-navy">Elever</label>
            <span class="text-xs font-bold text-navy/60">{{ parsedStudents.length }} upptäckta</span>
          </div>
          <p class="text-xs text-navy/60 mb-2">Klistra in en lista med namn, ett per rad.</p>
          <textarea
            v-model="rawStudents"
            rows="8"
            placeholder="Anna Andersson&#10;Björn Borg&#10;Cecilia Ceder"
            class="w-full border-2 border-navy p-3 text-sm font-mono whitespace-pre focus:outline-none focus:ring-4 focus:ring-navy/20 resize-y"
          />
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
            {{ isSubmitting ? 'Sparar...' : 'Spara Lista' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
