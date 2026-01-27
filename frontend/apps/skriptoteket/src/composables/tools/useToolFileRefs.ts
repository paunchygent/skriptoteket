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

  async function fetchFileRefs(toolId: string, context: string = DEFAULT_CONTEXT): Promise<void> {
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
      fileRefs.value = response.files ?? [];
    } catch {
      fileRefs.value = [];
    }
  }

  function reset(): void {
    fileRefs.value = [];
  }

  return {
    fileRefs,
    fetchFileRefs,
    reset,
  };
}
