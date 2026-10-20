import { ref, type Ref } from "vue";

import { apiFetchBlob, isApiError } from "../../api/client";
import { vaultFileDownloadPath } from "../../api/vaultFilePaths";
import type { components } from "../../api/openapi";
import type { useVaultFiles } from "../../composables/vault/useVaultFiles";
import { useToastStore } from "../../stores/toast";

type VaultFileInfo = components["schemas"]["VaultFileInfo"];
type VaultFileActionsOptions = Pick<ReturnType<typeof useVaultFiles>, "deleteFile" | "restoreFile" | "refresh"> & {
  selectedManageIds: Ref<string[]>;
  clearManageSelection: () => void;
};

const deleteFileFailureMessage = "Det gick inte att flytta filen till papperskorgen. Försök igen.";
const deleteFilesFailureMessage = "Det gick inte att flytta filerna till papperskorgen. Försök igen.";
const restoreFileFailureMessage = "Det gick inte att återställa filen. Försök igen.";
const restoreFilesFailureMessage = "Det gick inte att återställa filerna. Försök igen.";

export function useVaultFileActions({
  selectedManageIds,
  clearManageSelection,
  deleteFile,
  restoreFile,
  refresh,
}: VaultFileActionsOptions) {
  const toast = useToastStore();
  const actionError = ref<string | null>(null);
  const isMutating = ref(false);

  async function onDelete(fileId: string): Promise<void> {
    if (isMutating.value) return;
    isMutating.value = true;
    actionError.value = null;

    try {
      await deleteFile(fileId);
      toast.success("Filen flyttades till papperskorgen.");
      await refresh();
    } catch {
      toast.failure(deleteFileFailureMessage);
    } finally {
      isMutating.value = false;
    }
  }

  async function onDeleteSelected(): Promise<void> {
    if (isMutating.value) return;
    if (selectedManageIds.value.length === 0) return;

    isMutating.value = true;
    actionError.value = null;

    try {
      for (const fileId of selectedManageIds.value) {
        await deleteFile(fileId);
      }
      clearManageSelection();
      toast.success("Markerade filer flyttades till papperskorgen.");
      await refresh();
    } catch {
      toast.failure(deleteFilesFailureMessage);
    } finally {
      isMutating.value = false;
    }
  }

  async function onRestore(fileId: string): Promise<void> {
    if (isMutating.value) return;
    isMutating.value = true;
    actionError.value = null;

    try {
      await restoreFile(fileId);
      toast.success("Filen återställdes.");
      await refresh();
    } catch {
      toast.failure(restoreFileFailureMessage);
    } finally {
      isMutating.value = false;
    }
  }

  async function onRestoreSelected(): Promise<void> {
    if (isMutating.value) return;
    if (selectedManageIds.value.length === 0) return;

    isMutating.value = true;
    actionError.value = null;

    try {
      for (const fileId of selectedManageIds.value) {
        await restoreFile(fileId);
      }
      clearManageSelection();
      toast.success("Markerade filer återställdes.");
      await refresh();
    } catch {
      toast.failure(restoreFilesFailureMessage);
    } finally {
      isMutating.value = false;
    }
  }

  async function onDownload(file: VaultFileInfo): Promise<void> {
    if (isMutating.value) return;
    isMutating.value = true;
    actionError.value = null;

    try {
      const blob = await apiFetchBlob(downloadHref(file.id));
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = file.name;
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (error: unknown) {
      if (isApiError(error)) {
        const details = error.details as { resource?: string } | null;
        if (error.code === "NOT_FOUND" && details?.resource === "VaultFile") {
          actionError.value =
            "Filen saknas på servern. Ta bort filen och skapa den igen om du behöver den.";
        } else {
          actionError.value = error.message;
        }
      } else if (error instanceof Error) {
        actionError.value = error.message;
      } else {
        actionError.value = "Det gick inte att ladda ned filen.";
      }
    } finally {
      isMutating.value = false;
    }
  }

  function downloadHref(fileId: string): string {
    return vaultFileDownloadPath(fileId);
  }

  return {
    actionError,
    isMutating,
    onDelete,
    onDeleteSelected,
    onRestore,
    onRestoreSelected,
    onDownload,
  };
}
