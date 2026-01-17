import { ref, watch, type Ref } from "vue";

import type { components } from "../../api/openapi";

type EditorBootResponse = components["schemas"]["EditorBootResponse"];
type LayoutControls = {
  enable: () => void;
};

type UseScriptEditorFocusEffectsOptions = {
  layout: LayoutControls;
  focusMode: Readonly<Ref<boolean>>;
  editor: Readonly<Ref<EditorBootResponse | null>>;
  isChatDrawerOpen: Readonly<Ref<boolean>>;
};

export function useScriptEditorFocusEffects(options: UseScriptEditorFocusEffectsOptions): void {
  const { layout, focusMode, editor, isChatDrawerOpen } = options;
  const focusInitialized = ref(false);

  watch(
    () => isChatDrawerOpen.value,
    (open) => {
      if (!open) return;
      if (!focusMode.value) {
        layout.enable();
      }
    },
  );

  watch(
    () => editor.value,
    (value) => {
      if (!value || focusInitialized.value) return;
      focusInitialized.value = true;
      if (!focusMode.value) {
        layout.enable();
      }
    },
    { immediate: true },
  );
}
