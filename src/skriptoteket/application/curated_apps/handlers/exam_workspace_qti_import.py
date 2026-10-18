"""Import one QTI 3.0 package into the native exam workspace.

Purpose:
    Parse an uploaded QTI package into a native exam workspace container with no
    database and no AI call, and save revision one to Mina filer for a signed-in
    teacher synchronously, exactly like the DigiExam import lane.

Relationships:
    - ``ParseExamWorkspaceQtiPackageHandler`` is the stateless application entry
      the guest route (TASK-SKRIPT-41-02-02) calls and returns the document.
    - ``ImportExamWorkspaceQtiDocumentHandler`` reuses ``document_summary`` and
      ``ExamWorkspaceDocumentStore.save`` inside a store transaction so a reopen
      sees the same revision-one baseline the DOCX and DigiExam imports write.
    - Reads QTI through ``ExamNetQtiPackageReaderProtocol`` and maps it with
      ``domain.exam_workspace.qti_import``; it never reaches an AI client (Q1).
"""

from __future__ import annotations

import hashlib

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentSummary
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    document_summary,
    validated_exam_course,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_reader import (
    read_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.qti_import import (
    build_native_exam_from_qti,
)
from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.input_files import sanitize_input_filename
from skriptoteket.protocols.exam_workspace import (
    ExamNetQtiPackageReaderProtocol,
    ExamWorkspaceContainerCodecProtocol,
    ParseExamWorkspaceQtiPackageHandlerProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol


class ParseExamWorkspaceQtiPackageHandler:
    """Parse one uploaded QTI package into a container without any I/O."""

    def __init__(
        self,
        *,
        reader: ExamNetQtiPackageReaderProtocol,
        settings: Settings,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._reader = reader
        self._settings = settings
        self._id_generator = id_generator

    def handle(
        self, *, filename: str, content: bytes, course_key: str | None
    ) -> ExamWorkspaceContainerContent:
        safe_name = sanitize_input_filename(input_filename=filename)
        if not safe_name.lower().endswith(".zip"):
            raise validation_error(
                "Välj en .zip-fil med ett QTI-paket.", details={"filename": safe_name}
            )
        if not content:
            raise validation_error("Filen saknar innehåll.")
        if len(content) > self._settings.VAULT_MAX_FILE_BYTES:
            raise validation_error("Filen är större än maxstorleken för Mina filer.")

        course = validated_exam_course(course_key)
        source = self._reader.read(content=content)
        items = read_examnet_qti_items(source)
        return build_native_exam_from_qti(
            items=items,
            document_id=self._id_generator.new_uuid(),
            source_filename=safe_name,
            source_sha256=hashlib.sha256(content).hexdigest(),
            course=course,
        )


class ImportExamWorkspaceQtiDocumentHandler:
    """Parse and save one QTI package as revision one in Mina filer."""

    def __init__(
        self,
        *,
        parse: ParseExamWorkspaceQtiPackageHandlerProtocol,
        store: ExamWorkspaceDocumentStore,
        codec: ExamWorkspaceContainerCodecProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._parse = parse
        self._store = store
        self._codec = codec
        self._id_generator = id_generator

    async def handle(
        self, *, actor: User, filename: str, content: bytes, course_key: str | None
    ) -> ExamWorkspaceDocumentSummary:
        container = self._parse.handle(filename=filename, content=content, course_key=course_key)
        lineage_id = container.document.document_id
        encoded = self._codec.build(content=container)
        async with self._store.transaction(user_id=actor.id, lineage_id=lineage_id):
            vault_file = await self._store.save(
                actor=actor,
                file_id=self._id_generator.new_uuid(),
                name=f"{container.document.title}.provdokument.zip",
                content=encoded,
                lineage_id=lineage_id,
                version=1,
            )
        return document_summary(vault_file, container.document)
