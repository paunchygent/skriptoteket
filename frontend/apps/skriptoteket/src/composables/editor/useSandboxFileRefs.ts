import { ref, type Ref } from "vue";

import { apiGet } from "../../api/client";
import { useAuthStore } from "../../stores/auth";
import type { FileRefInfo } from "../tools/fileRefHelpers";

type SandboxFileRefsResponse = {
  tool_id: string;
  version_id: string;
  snapshot_id: string;
  files: FileRefInfo[];
};

type UseSandboxFileRefsOptions = {
  versionId: Readonly<Ref<string>>;
};

export function useSandboxFileRefs({ versionId }: UseSandboxFileRefsOptions) {
  const fileRefs = ref<FileRefInfo[]>([]);
  const auth = useAuthStore();

  async function fetchFileRefs(snapshotId: string): Promise<void> {
    if (!versionId.value || !snapshotId) {
      fileRefs.value = [];
      return;
    }
    if (!auth.bootstrapped || !auth.isAuthenticated) {
      fileRefs.value = [];
      return;
    }
    try {
      const response = await apiGet<SandboxFileRefsResponse>(
        `/api/v1/editor/tool-versions/${encodeURIComponent(versionId.value)}/file-refs` +
          `?snapshot_id=${encodeURIComponent(snapshotId)}`,
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
