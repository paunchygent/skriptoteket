<script setup lang="ts">
import type { components } from "../../api/openapi";
import type { EditorWorkingCopyCheckpointSummary } from "../../composables/editor/useEditorWorkingCopy";

import InstructionsDrawer from "./InstructionsDrawer.vue";
import MaintainersDrawer from "./MaintainersDrawer.vue";
import MetadataDrawer from "./MetadataDrawer.vue";
import VersionHistoryDrawer from "./VersionHistoryDrawer.vue";

type EditorVersionSummary = components["schemas"]["EditorVersionSummary"];
type ProfessionItem = components["schemas"]["ProfessionItem"];
type CategoryItem = components["schemas"]["CategoryItem"];
type MaintainerSummary = components["schemas"]["MaintainerSummary"];

type EditorWorkspaceDrawersProps = {
  isHistoryDrawerOpen: boolean;
  isMetadataDrawerOpen: boolean;
  isMaintainersDrawerOpen: boolean;
  isInstructionsDrawerOpen: boolean;

  versions: EditorVersionSummary[];
  activeVersionId: string | null;

  canRollbackVersions: boolean;
  isWorkflowSubmitting: boolean;
  checkpoints: EditorWorkingCopyCheckpointSummary[];
  pinnedCheckpointCount: number;
  pinnedCheckpointLimit: number;
  isCheckpointBusy: boolean;

  metadataTitle: string;
  metadataSlug: string;
  metadataSummary: string;
  canEditSlug: boolean;
  slugError: string | null;

  professions: ProfessionItem[];
  categories: CategoryItem[];
  selectedProfessionIds: string[];
  selectedCategoryIds: string[];
  taxonomyError: string | null;
  isTaxonomyLoading: boolean;
  isSavingAllMetadata: boolean;

  maintainers: MaintainerSummary[];
  ownerUserId: string | null;
  isMaintainersLoading: boolean;
  isMaintainersSaving: boolean;
  maintainersError: string | null;

  usageInstructions: string;
  isSaving: boolean;
  isReadOnly: boolean;
};

const props = defineProps<EditorWorkspaceDrawersProps>();

const emit = defineEmits<{
  (event: "close"): void;
  (event: "selectHistoryVersion", versionId: string): void;
  (event: "compareVersion", versionId: string): void;
  (event: "rollbackVersion", versionId: string): void;
  (event: "saveAllMetadata"): void;
  (event: "suggestSlugFromTitle"): void;
  (event: "addMaintainer", email: string): void;
  (event: "removeMaintainer", userId: string): void;
  (event: "save"): void;
  (event: "createCheckpoint", label: string): void;
  (event: "restoreCheckpoint", checkpointId: string): void;
  (event: "removeCheckpoint", checkpointId: string): void;
  (event: "restoreServerVersion"): void;
  (event: "update:usageInstructions", value: string): void;
  (event: "update:metadataTitle", value: string): void;
  (event: "update:metadataSlug", value: string): void;
  (event: "update:metadataSummary", value: string): void;
  (event: "update:slugError", value: string | null): void;
  (event: "update:taxonomyError", value: string | null): void;
  (event: "update:maintainersError", value: string | null): void;
  (event: "update:selectedProfessionIds", value: string[]): void;
  (event: "update:selectedCategoryIds", value: string[]): void;
}>();
</script>

<template>
  <VersionHistoryDrawer
    v-if="props.isHistoryDrawerOpen"
    :is-open="props.isHistoryDrawerOpen"
    :versions="props.versions"
    :active-version-id="props.activeVersionId"
    :can-rollback="props.canRollbackVersions"
    :is-submitting="props.isWorkflowSubmitting"
    :checkpoints="props.checkpoints"
    :pinned-checkpoint-count="props.pinnedCheckpointCount"
    :pinned-checkpoint-limit="props.pinnedCheckpointLimit"
    :is-checkpoint-busy="props.isCheckpointBusy"
    @close="emit('close')"
    @select="emit('selectHistoryVersion', $event)"
    @compare="emit('compareVersion', $event)"
    @rollback="emit('rollbackVersion', $event)"
    @create-checkpoint="emit('createCheckpoint', $event)"
    @restore-checkpoint="emit('restoreCheckpoint', $event)"
    @remove-checkpoint="emit('removeCheckpoint', $event)"
    @restore-server-version="emit('restoreServerVersion')"
  />

  <MetadataDrawer
    v-if="props.isMetadataDrawerOpen"
    :is-open="props.isMetadataDrawerOpen"
    :metadata-title="props.metadataTitle"
    :metadata-slug="props.metadataSlug"
    :metadata-summary="props.metadataSummary"
    :can-edit-slug="props.canEditSlug"
    :slug-error="props.slugError"
    :professions="props.professions"
    :categories="props.categories"
    :selected-profession-ids="props.selectedProfessionIds"
    :selected-category-ids="props.selectedCategoryIds"
    :taxonomy-error="props.taxonomyError"
    :is-loading="props.isTaxonomyLoading"
    :is-saving="props.isSavingAllMetadata"
    @close="emit('close')"
    @save="emit('saveAllMetadata')"
    @update:metadata-title="emit('update:metadataTitle', $event)"
    @update:metadata-slug="emit('update:metadataSlug', $event)"
    @update:metadata-summary="emit('update:metadataSummary', $event)"
    @update:slug-error="emit('update:slugError', $event)"
    @suggest-slug-from-title="emit('suggestSlugFromTitle')"
    @update:selected-profession-ids="emit('update:selectedProfessionIds', $event)"
    @update:selected-category-ids="emit('update:selectedCategoryIds', $event)"
    @update:taxonomy-error="emit('update:taxonomyError', $event)"
  />

  <MaintainersDrawer
    v-if="props.isMaintainersDrawerOpen"
    :is-open="props.isMaintainersDrawerOpen"
    :maintainers="props.maintainers"
    :owner-user-id="props.ownerUserId"
    :is-superuser="props.canRollbackVersions"
    :is-loading="props.isMaintainersLoading"
    :is-saving="props.isMaintainersSaving"
    :error="props.maintainersError"
    @close="emit('close')"
    @add="emit('addMaintainer', $event)"
    @remove="emit('removeMaintainer', $event)"
    @update:error="emit('update:maintainersError', $event)"
  />

  <InstructionsDrawer
    v-if="props.isInstructionsDrawerOpen"
    :is-open="props.isInstructionsDrawerOpen"
    :usage-instructions="props.usageInstructions"
    :is-saving="props.isSaving"
    :is-read-only="props.isReadOnly"
    @close="emit('close')"
    @save="emit('save')"
    @update:usage-instructions="emit('update:usageInstructions', $event)"
  />
</template>
