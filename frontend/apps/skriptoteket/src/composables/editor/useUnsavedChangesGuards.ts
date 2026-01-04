import { computed, onBeforeUnmount, onMounted, type Ref } from "vue";
import { onBeforeRouteLeave } from "vue-router";

type UseUnsavedChangesGuardsOptions = {
  hasDirtyChanges: Readonly<Ref<boolean>>;
  isSaving: Readonly<Ref<boolean>>;
};

const ROUTE_LEAVE_MESSAGE = "Du har osparade ändringar. Vill du lämna sidan?";

export function useUnsavedChangesGuards({ hasDirtyChanges, isSaving }: UseUnsavedChangesGuardsOptions) {
  const hasBlockingUnsavedChanges = computed(() => hasDirtyChanges.value && !isSaving.value);

  function confirmDiscardChanges(message: string): boolean {
    if (!hasBlockingUnsavedChanges.value) return true;
    return window.confirm(message);
  }

  const beforeUnloadHandler = (event: BeforeUnloadEvent) => {
    if (!hasBlockingUnsavedChanges.value) return;
    event.preventDefault();
    event.returnValue = "";
  };

  onBeforeRouteLeave((_to, _from, next) => {
    if (!hasBlockingUnsavedChanges.value) {
      next();
      return;
    }

    if (confirmDiscardChanges(ROUTE_LEAVE_MESSAGE)) {
      next();
    } else {
      next(false);
    }
  });

  onMounted(() => {
    window.addEventListener("beforeunload", beforeUnloadHandler);
  });

  onBeforeUnmount(() => {
    window.removeEventListener("beforeunload", beforeUnloadHandler);
  });

  return {
    hasBlockingUnsavedChanges,
    confirmDiscardChanges,
  };
}
