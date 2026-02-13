import { ref } from "vue";

import type { Ref } from "vue";

import { apiFetch, apiPost, isApiError } from "../../api/client";
import { useToast } from "../useToast";

import type {
  ReagentPrepChefDefaultsResult,
  ReagentPrepChefLoadDefaultsRequest,
  ReagentPrepChefPrepRequestInput,
  ReagentPrepChefPrepRequestOutput,
  ReagentPrepChefSaveDefaultsResult,
  ReagentPrepChefUpdateDefaultsRequest,
} from "../../views/apps/reagent-prep-chef/types";

type DefaultsOptions = {
  apiPrefix: Ref<string>;
  canCalculate: Ref<boolean>;
  buildRequestPayload: () => ReagentPrepChefPrepRequestInput;
  applyDefaults: (preset: ReagentPrepChefPrepRequestOutput) => void;
  actionErrorMessage: Ref<string | null>;
};

export function useReagentPrepChefDefaults(options: DefaultsOptions) {
  const toast = useToast();
  const defaults = ref<ReagentPrepChefDefaultsResult | null>(null);
  const defaultsStateRev = ref(0);
  const isDefaultsLoading = ref(false);
  const isDefaultsSaving = ref(false);
  const isSavingDefaultsToVault = ref(false);
  const lastSavedDefaultsVaultRef = ref<string | null>(null);
  const isLoadingDefaultsFromVault = ref(false);
  const isDefaultsVaultPickerOpen = ref(false);
  const defaultsVaultPickerDraft = ref<string[]>([]);

  async function fetchDefaults(): Promise<void> {
    isDefaultsLoading.value = true;
    try {
      const response = await apiGetDefaults();
      defaults.value = response;
      defaultsStateRev.value = response.state_rev;
    } finally {
      isDefaultsLoading.value = false;
    }
  }

  async function apiGetDefaults(): Promise<ReagentPrepChefDefaultsResult> {
    return apiFetch<ReagentPrepChefDefaultsResult>(`${options.apiPrefix.value}/defaults`);
  }

  async function saveDefaults(): Promise<void> {
    if (isDefaultsSaving.value) return;

    isDefaultsSaving.value = true;
    options.actionErrorMessage.value = null;

    const payload: ReagentPrepChefUpdateDefaultsRequest = {
      expected_state_rev: defaultsStateRev.value,
      defaults: options.buildRequestPayload(),
    };

    try {
      const response = await apiFetch<ReagentPrepChefDefaultsResult>(
        `${options.apiPrefix.value}/defaults`,
        {
          method: "PUT",
          body: payload,
        },
      );
      defaults.value = response;
      defaultsStateRev.value = response.state_rev;
      toast.success("Standardinställningar sparade.");
    } catch (error: unknown) {
      if (isApiError(error)) {
        options.actionErrorMessage.value = error.message;
      } else if (error instanceof Error) {
        options.actionErrorMessage.value = error.message;
      } else {
        options.actionErrorMessage.value = "Det gick inte att spara standardinställningarna.";
      }
    } finally {
      isDefaultsSaving.value = false;
    }
  }

  async function clearDefaults(): Promise<void> {
    if (isDefaultsSaving.value) return;

    isDefaultsSaving.value = true;
    options.actionErrorMessage.value = null;

    const payload: ReagentPrepChefUpdateDefaultsRequest = {
      expected_state_rev: defaultsStateRev.value,
      defaults: null,
    };

    try {
      const response = await apiFetch<ReagentPrepChefDefaultsResult>(
        `${options.apiPrefix.value}/defaults`,
        {
          method: "PUT",
          body: payload,
        },
      );
      defaults.value = response;
      defaultsStateRev.value = response.state_rev;
      toast.success("Standardinställningar rensade.");
    } catch (error: unknown) {
      if (isApiError(error)) {
        options.actionErrorMessage.value = error.message;
      } else if (error instanceof Error) {
        options.actionErrorMessage.value = error.message;
      } else {
        options.actionErrorMessage.value = "Det gick inte att rensa standardinställningarna.";
      }
    } finally {
      isDefaultsSaving.value = false;
    }
  }

  function defaultVaultDefaultsName(): string {
    return "reagensberedning-standardinstallningar.json";
  }

  function vaultFileIdFromRef(refValue: string): string | null {
    const prefix = "vault:";
    if (!refValue.startsWith(prefix)) return null;
    const candidate = refValue.slice(prefix.length).trim();
    return candidate.length > 0 ? candidate : null;
  }

  async function saveDefaultsToVault(): Promise<void> {
    if (!options.canCalculate.value) return;
    if (isSavingDefaultsToVault.value) return;

    isSavingDefaultsToVault.value = true;
    options.actionErrorMessage.value = null;

    try {
      const response = await apiPost<ReagentPrepChefSaveDefaultsResult>(
        `${options.apiPrefix.value}/save-defaults`,
        {
          defaults: options.buildRequestPayload(),
          name: defaultVaultDefaultsName(),
        },
      );
      lastSavedDefaultsVaultRef.value = response.file.ref;
      toast.success("Standardinställningar sparade i Mina filer.");
    } catch (error: unknown) {
      if (isApiError(error)) {
        options.actionErrorMessage.value = error.message;
      } else if (error instanceof Error) {
        options.actionErrorMessage.value = error.message;
      } else {
        options.actionErrorMessage.value =
          "Det gick inte att spara standardinställningarna i Mina filer just nu.";
      }
    } finally {
      isSavingDefaultsToVault.value = false;
    }
  }

  function openDefaultsVaultPicker(): void {
    defaultsVaultPickerDraft.value = [];
    isDefaultsVaultPickerOpen.value = true;
  }

  function closeDefaultsVaultPicker(): void {
    isDefaultsVaultPickerOpen.value = false;
  }

  async function loadDefaultsFromVaultFileRef(refValue: string): Promise<void> {
    const fileId = vaultFileIdFromRef(refValue);
    if (!fileId) {
      options.actionErrorMessage.value = "Ogiltig filreferens. Välj en fil från Mina filer igen.";
      return;
    }

    if (isLoadingDefaultsFromVault.value) return;

    isLoadingDefaultsFromVault.value = true;
    options.actionErrorMessage.value = null;

    const payload: ReagentPrepChefLoadDefaultsRequest = {
      expected_state_rev: defaultsStateRev.value,
      file_id: fileId,
    };

    try {
      const response = await apiPost<ReagentPrepChefDefaultsResult>(
        `${options.apiPrefix.value}/load-defaults`,
        payload,
      );
      defaults.value = response;
      defaultsStateRev.value = response.state_rev;

      if (!response.defaults) {
        toast.info("Filen innehöll inga standardinställningar.");
        return;
      }

      options.applyDefaults(response.defaults);
      toast.success("Standardinställningar laddade från Mina filer.");
    } catch (error: unknown) {
      if (isApiError(error)) {
        options.actionErrorMessage.value = error.message;
      } else if (error instanceof Error) {
        options.actionErrorMessage.value = error.message;
      } else {
        options.actionErrorMessage.value =
          "Det gick inte att ladda standardinställningar från Mina filer.";
      }
    } finally {
      isLoadingDefaultsFromVault.value = false;
    }
  }

  function onDefaultsVaultPickerConfirm(refs: string[]): void {
    closeDefaultsVaultPicker();
    const refValue = refs.at(0);
    if (!refValue) return;
    void loadDefaultsFromVaultFileRef(refValue);
  }

  return {
    defaults,
    defaultsStateRev,
    isDefaultsLoading,
    isDefaultsSaving,
    isSavingDefaultsToVault,
    lastSavedDefaultsVaultRef,
    isLoadingDefaultsFromVault,
    isDefaultsVaultPickerOpen,
    defaultsVaultPickerDraft,
    fetchDefaults,
    saveDefaults,
    clearDefaults,
    saveDefaultsToVault,
    openDefaultsVaultPicker,
    closeDefaultsVaultPicker,
    loadDefaultsFromVaultFileRef,
    onDefaultsVaultPickerConfirm,
  };
}
