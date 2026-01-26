import { computed, ref } from "vue";
import { useRouter } from "vue-router";

import { apiPost, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { useToast } from "../useToast";

type CreateDraftToolResponse = components["schemas"]["CreateDraftToolResponse"];

function normalizedOptionalString(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export function useCreateDraftToolModal() {
  const router = useRouter();
  const toast = useToast();

  const isOpen = ref(false);
  const title = ref("");
  const summary = ref("");
  const error = ref<string | null>(null);
  const isSubmitting = ref(false);

  const canSubmit = computed(() => Boolean(title.value.trim()) && !isSubmitting.value);

  function open(): void {
    title.value = "";
    summary.value = "";
    error.value = null;
    isOpen.value = true;
  }

  function close(): void {
    isOpen.value = false;
    error.value = null;
  }

  async function submit(): Promise<void> {
    if (isSubmitting.value) return;

    const trimmedTitle = title.value.trim();
    if (!trimmedTitle) {
      error.value = "Titel krävs.";
      return;
    }

    isSubmitting.value = true;
    error.value = null;

    try {
      const response = await apiPost<CreateDraftToolResponse>("/api/v1/admin/tools", {
        title: trimmedTitle,
        summary: normalizedOptionalString(summary.value),
      });

      close();
      toast.success("Verktyg skapat.");
      await router.push(`/admin/tools/${response.tool.id}`);
    } catch (caught: unknown) {
      if (isApiError(caught)) {
        error.value = caught.message;
      } else if (caught instanceof Error) {
        error.value = caught.message;
      } else {
        error.value = "Det gick inte att skapa verktyget.";
      }
    } finally {
      isSubmitting.value = false;
    }
  }

  return {
    isOpen,
    title,
    summary,
    error,
    isSubmitting,
    canSubmit,
    open,
    close,
    submit,
  };
}
