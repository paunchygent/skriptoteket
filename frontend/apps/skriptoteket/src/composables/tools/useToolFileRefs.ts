import { ref } from "vue";

import { apiGet } from "../../api/client";
import { useAuthStore } from "../../stores/auth";
import type { FileRefInfo } from "./fileRefHelpers";

type ToolFileRefsResponse = {
  tool_id: string;
  context: string;
  files: FileRefInfo[];
};

const DEFAULT_CONTEXT = "default";

export function useToolFileRefs() {
  const fileRefs = ref<FileRefInfo[]>([]);
  const auth = useAuthStore();
  let requestGeneration = 0;

  async function fetchFileRefs(toolId: string, context: string = DEFAULT_CONTEXT): Promise<void> {
    const generation = ++requestGeneration;
    if (!toolId) {
      fileRefs.value = [];
      return;
    }
    if (!auth.bootstrapped || !auth.isAuthenticated) {
      fileRefs.value = [];
      return;
    }
    try {
      const response = await apiGet<ToolFileRefsResponse>(
        `/api/v1/tools/${encodeURIComponent(toolId)}/file-refs?context=${encodeURIComponent(context)}`,
      );
      if (generation === requestGeneration) {
        fileRefs.value = response.files ?? [];
      }
    } catch {
      if (generation === requestGeneration) {
        fileRefs.value = [];
      }
    }
  }

  function reset(): void {
    requestGeneration += 1;
    fileRefs.value = [];
  }

  return {
    fileRefs,
    fetchFileRefs,
    reset,
  };
}
