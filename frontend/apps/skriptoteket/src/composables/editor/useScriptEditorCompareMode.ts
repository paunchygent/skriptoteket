import { computed, ref, watch, type Ref } from "vue";
import type { RouteLocationNormalizedLoaded, Router } from "vue-router";

import type { components } from "../../api/openapi";
import {
  resolveDefaultCompareTarget,
  resolveMostRecentRejectedReviewVersionId,
} from "./editorCompareDefaults";
import { useEditorCompareState, type EditorCompareTarget } from "./useEditorCompareState";
import { isVirtualFileId } from "./virtualFiles";

type EditorBootResponse = components["schemas"]["EditorBootResponse"];
type SelectedVersion = EditorBootResponse["selected_version"];

export type EditorWorkspaceMode = "source" | "diff" | "metadata" | "test";

type UseScriptEditorCompareModeOptions = {
  route: RouteLocationNormalizedLoaded;
  router: Router;
  editor: Readonly<Ref<EditorBootResponse | null>>;
  selectedVersion: Readonly<Ref<SelectedVersion | null>>;
  onCompareVersion?: () => void;
};

export function useScriptEditorCompareMode(options: UseScriptEditorCompareModeOptions) {
  const { route, router, editor, selectedVersion, onCompareVersion } = options;

  const compare = useEditorCompareState({ route, router });
  const compareTarget = compare.compareTarget;
  const compareActiveFileId = compare.activeFileId;

  const rejectedReviewVersionId = computed(() => {
    if (!editor.value) return null;
    return resolveMostRecentRejectedReviewVersionId(editor.value.versions);
  });

  const defaultCompareTarget = computed(() => {
    if (!editor.value) {
      return { target: null, reason: null } as const;
    }
    return resolveDefaultCompareTarget({
      baseVersion: selectedVersion.value,
      toolIsPublished: editor.value.tool.is_published,
      activeVersionId: editor.value.tool.active_version_id ?? null,
      versions: editor.value.versions,
      parentVersionId: editor.value.parent_version_id ?? null,
    });
  });

  const canOpenCompare = computed(
    () => compareTarget.value === null && defaultCompareTarget.value.target !== null,
  );
  const openCompareTitle = computed(() => defaultCompareTarget.value.reason ?? "");

  const canCompareVersions = computed(() => {
    if (!editor.value) return true;
    if (selectedVersion.value?.state !== "in_review") return true;
    if (editor.value.tool.is_published) return true;
    return rejectedReviewVersionId.value !== null;
  });

  async function handleCompareVersion(versionId: string): Promise<void> {
    await compare.toggleCompareVersionId(versionId);
    onCompareVersion?.();
  }

  async function handleOpenCompare(): Promise<void> {
    const target = defaultCompareTarget.value.target;
    if (!target) return;
    await compare.setCompareTarget(target);
  }

  async function handleCompareTargetUpdate(target: EditorCompareTarget | null): Promise<void> {
    await compare.setCompareTarget(target);
  }

  async function handleCompareActiveFileIdUpdate(fileId: unknown): Promise<void> {
    if (!isVirtualFileId(fileId)) {
      return;
    }
    await compare.setActiveFileId(fileId);
  }

  async function handleCloseCompare(): Promise<void> {
    await compare.closeCompare();
  }

  const editorMode = ref<EditorWorkspaceMode>("source");
  const canEnterDiff = computed(() => true);

  function setEditorMode(nextMode: EditorWorkspaceMode): void {
    if (nextMode === editorMode.value) {
      if (nextMode === "diff") {
        void handleCloseCompare();
        editorMode.value = "source";
      }
      if (nextMode === "metadata" || nextMode === "test") {
        editorMode.value = "source";
      }
      return;
    }

    if (nextMode === "diff") {
      if (compareTarget.value) {
        editorMode.value = "diff";
        return;
      }
      if (!canOpenCompare.value) {
        editorMode.value = "diff";
        return;
      }
      editorMode.value = "diff";
      void handleOpenCompare();
      return;
    }

    if (compareTarget.value) {
      void handleCloseCompare();
    }

    editorMode.value = nextMode;
  }

  function handleAiProposalReady(): void {
    if (editorMode.value !== "source") {
      editorMode.value = "source";
    }
  }

  watch(
    () => compareTarget.value,
    (value) => {
      if (value && editorMode.value !== "diff") {
        editorMode.value = "diff";
      }
      if (!value && editorMode.value === "diff") {
        editorMode.value = "source";
      }
    },
  );

  return {
    compareTarget,
    compareActiveFileId,
    openCompareTitle,
    canCompareVersions,
    canOpenCompare,
    editorMode,
    canEnterDiff,
    setEditorMode,
    handleCompareVersion,
    handleCloseCompare,
    handleCompareTargetUpdate,
    handleCompareActiveFileIdUpdate,
    handleAiProposalReady,
  };
}
