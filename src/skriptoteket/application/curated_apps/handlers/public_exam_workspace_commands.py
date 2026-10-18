"""Stateless guest document commands over the browser-held exam (B2b).

Purpose:
    Run one server-side document command for a guest: the request carries the
    whole document and the response carries the result, so the handler holds no
    vault, store or UoW and reaches nothing server-held.

Relationships:
    - Reuses the exact domain functions the signed-in workspace handlers call
      (``native_exam_parent_commands``, ``change_item_type``), and takes its
      ``random.Random`` from DI like the signed-in change-type handler.
"""

import random
from collections.abc import Callable

from skriptoteket.application.curated_apps.public_exam_workspace import (
    PublicExamBlankResponse,
    PublicExamChangeTypeResponse,
    PublicExamDocumentCommandResponse,
    PublicExamDocumentDeleteResponse,
)
from skriptoteket.domain.curated_apps.exam_workspace import (
    native_exam_parent_commands as commands,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_blank import (
    blank_native_exam_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeParagraph
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_change_type import (
    change_item_type,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)


class PublicExamWorkspaceCommandHandler:
    def __init__(self, *, rng: random.Random) -> None:
        self._rng = rng

    def blank(self) -> PublicExamBlankResponse:
        return PublicExamBlankResponse(document=blank_native_exam_document())

    def create_parent(
        self,
        *,
        document: NativeExamDocument,
        instruction: tuple[NativeParagraph, ...],
        child: NativeExamItem,
        position: int,
    ) -> PublicExamDocumentCommandResponse:
        return PublicExamDocumentCommandResponse(
            document=commands.create_parent(
                document,
                instruction=instruction,
                child=child,
                position=position,
            )
        )

    def add_child(
        self,
        *,
        document: NativeExamDocument,
        parent_id: str,
        child: NativeExamItem,
        position: int,
    ) -> PublicExamDocumentCommandResponse:
        return PublicExamDocumentCommandResponse(
            document=commands.add_child(
                document, parent_id=parent_id, child=child, position=position
            )
        )

    def delete_child(
        self, *, document: NativeExamDocument, parent_id: str, item_id: str
    ) -> PublicExamDocumentDeleteResponse:
        return self._delete(
            document=document,
            parent_id=parent_id,
            operation=lambda current: commands.delete_child(
                current, parent_id=parent_id, item_id=item_id
            ),
        )

    def delete_parent(
        self, *, document: NativeExamDocument, parent_id: str, mode: str
    ) -> PublicExamDocumentDeleteResponse:
        if mode == "with_questions":
            return self._delete(
                document=document,
                parent_id=parent_id,
                operation=lambda current: commands.delete_parent_with_children(
                    current, parent_id=parent_id
                ),
            )
        return self._delete(
            document=document,
            parent_id=parent_id,
            operation=lambda current: commands.delete_parent(current, parent_id=parent_id),
        )

    def reorder_children(
        self, *, document: NativeExamDocument, parent_id: str, item_ids: tuple[str, ...]
    ) -> PublicExamDocumentCommandResponse:
        return PublicExamDocumentCommandResponse(
            document=commands.reorder_children(document, parent_id=parent_id, item_ids=item_ids)
        )

    def change_type(
        self,
        *,
        document: NativeExamDocument,
        item_id: str,
        target_kind: NativeExamItemKind,
    ) -> PublicExamChangeTypeResponse:
        result = change_item_type(document, item_id=item_id, target_kind=target_kind, rng=self._rng)
        return PublicExamChangeTypeResponse(
            document=result.document, dropped_content=result.dropped_content
        )

    def _delete(
        self,
        *,
        document: NativeExamDocument,
        parent_id: str,
        operation: Callable[[NativeExamDocument], NativeExamDocument],
    ) -> PublicExamDocumentDeleteResponse:
        result = operation(document)
        removed_parent_id = (
            None if any(parent.parent_id == parent_id for parent in result.parents) else parent_id
        )
        return PublicExamDocumentDeleteResponse(
            document=result, removed_parent_id=removed_parent_id
        )
