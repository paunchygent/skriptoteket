/** Shared mounting for the exam workspace header specs (TASK-SKRIPT-40-04-17). */

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import type { Pinia } from "pinia";

import ExamWorkspaceHeader from "./ExamWorkspaceHeader.vue";
import { examWorkspaceProvidersPlugin } from "./examWorkspaceProviders.specSupport";

export type HeaderProps = InstanceType<typeof ExamWorkspaceHeader>["$props"];

export function headerProps(overrides: Partial<HeaderProps> = {}): HeaderProps {
  return {
    title: "Prov 1",
    saveState: "saved",
    saveText: "Sparat 14:05",
    saveTitle: null,
    courseLabel: "Kurs",
    total: 3,
    detailsOpen: false,
    openDrawerOpen: false,
    canRename: true,
    canSaveAs: true,
    suggestBusy: false,
    suggestDisabled: false,
    isPhone: false,
    previewOpen: false,
    ...overrides,
  };
}

export function mountHeader(overrides: Partial<HeaderProps> = {}, pinia: Pinia = createPinia()) {
  setActivePinia(pinia);
  return mount(ExamWorkspaceHeader, {
    props: headerProps(overrides),
    attachTo: document.body,
    slots: { export: '<button data-test="exam-workspace-export" class="xw-cmd">Exportera</button>' },
    global: { plugins: [pinia, examWorkspaceProvidersPlugin()] },
  });
}
