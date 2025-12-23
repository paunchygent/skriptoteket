import { ref } from "vue";

const isOpen = ref(false);
const redirectTo = ref<string | null>(null);

export function useLoginModal() {
  function open(redirect?: string) {
    redirectTo.value = redirect ?? null;
    isOpen.value = true;
  }

  function close() {
    isOpen.value = false;
    redirectTo.value = null;
  }

  return {
    isOpen,
    redirectTo,
    open,
    close,
  };
}
