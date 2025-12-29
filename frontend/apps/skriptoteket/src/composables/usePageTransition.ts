import { ref } from "vue";

const suppressNextPageTransition = ref(false);

export function usePageTransition() {
  function suppressNext(): void {
    suppressNextPageTransition.value = true;
  }

  function reset(): void {
    suppressNextPageTransition.value = false;
  }

  return {
    suppressNextPageTransition,
    suppressNext,
    reset,
  };
}
