import { useToastStore } from "../stores/toast";

export function useToast() {
  return useToastStore();
}
