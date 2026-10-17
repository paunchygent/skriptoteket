<script setup lang="ts">
import { isMacPlatform, examWorkspaceShortcut } from "../../../views/apps/exam-workspace/examWorkspaceFormat";
import HelpTopicLayout from "../HelpTopicLayout.vue";
import { useHelp } from "../useHelp";

const { showIndex } = useHelp();
const mac = isMacPlatform();
const keys: [string, string][] = [
  [examWorkspaceShortcut("S", false, mac), "Spara"],
  [examWorkspaceShortcut("Z", false, mac), "Ångra"],
  [examWorkspaceShortcut("Z", true, mac), "Gör om"],
  ["↑ ↓", "Föregående och nästa fråga i listan"],
];
</script>

<template>
  <HelpTopicLayout
    title="Provredigering"
    @back="showIndex"
  >
    <ul class="list-disc pl-5 space-y-2 text-sm text-navy">
      <li>Öppna importerar ett prov från Word (.docx) eller DigiExam (.dxe) och öppnar sparade prov.</li>
      <li>
        Ändringar sparas automatiskt som utkast, och Ångra och Gör om går igenom dem. Spara skriver
        över provet i Mina filer; Spara som gör en kopia med ett nytt namn.
      </li>
      <li>Import på en fråga visar hur frågan stod i provfilen och vad konverteringen bestämde.</li>
      <li>
        Exportera skapar QTI för Exam.net, PDF för utskrift eller Word från det sparade provet. Frågor
        som stoppar exporten listas först.
      </li>
    </ul>
    <h4 class="text-sm font-semibold text-navy">
      Kortkommandon
    </h4>
    <dl
      class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm text-navy"
      data-test="help-exam-workspace-keys"
    >
      <template
        v-for="[key, action] in keys"
        :key="action"
      >
        <dt class="justify-self-start rounded border border-navy/15 bg-canvas px-1.5 font-mono text-xs leading-6">
          {{ key }}
        </dt>
        <dd>{{ action }}</dd>
      </template>
    </dl>
  </HelpTopicLayout>
</template>
