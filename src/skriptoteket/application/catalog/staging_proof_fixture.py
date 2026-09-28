"""Create the repeatable Hemma staging proof fixture.

Purpose:
    Give the imported HuleEdu staging proof contributor one harmless staging
    tool that it maintains, with a draft it created, so the staging browser
    walk can lock and run that draft in the editor sandbox.

Relationships:
    - Reuses the catalog and scripting command handlers; it adds no new
      authorization rules.
    - Runs after `consume-huleedu-subject-export --apply` has created the
      proof admin and proof contributor users.
    - `cli/commands/setup_staging_proof_fixture.py` wires PostgreSQL adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from skriptoteket.application.catalog.commands import (
    AssignMaintainerCommand,
    CreateDraftToolCommand,
    UpdateToolSlugCommand,
)
from skriptoteket.application.identity.huleedu_subject_export_contract import (
    HuleEduSubjectExport,
)
from skriptoteket.application.scripting.commands import CreateDraftVersionCommand
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.protocols.catalog import (
    AssignMaintainerHandlerProtocol,
    CreateDraftToolHandlerProtocol,
    ToolMaintainerRepositoryProtocol,
    ToolRepositoryProtocol,
    UpdateToolSlugHandlerProtocol,
)
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.scripting import (
    CreateDraftVersionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

STAGING_PROOF_ADMIN_KEY = "skriptoteket-proof-admin"
STAGING_PROOF_CONTRIBUTOR_KEY = "skriptoteket-proof-contributor"
STAGING_PROOF_TOOL_SLUG = "staging-provverktyg"
STAGING_PROOF_TOOL_TITLE = "Staging-provverktyg"
STAGING_PROOF_TOOL_SUMMARY = "Ofarligt verktyg för provkörning i Hemma-staging."
STAGING_PROOF_SOURCE_CODE = """\
def run_tool(input_dir: str, output_dir: str) -> dict:
    del input_dir, output_dir
    return {
        "outputs": [
            {
                "kind": "notice",
                "level": "info",
                "message": "Staging-provkörningen är klar.",
            }
        ],
        "next_actions": [],
        "state": None,
    }
"""


@dataclass(frozen=True, slots=True)
class StagingProofFixtureResult:
    """Sanitized outcome of one fixture run."""

    tool_id: UUID
    tool_slug: str
    draft_version_id: UUID
    created_tool: bool
    assigned_maintainer: bool
    created_draft: bool


class StagingProofFixture:
    """Idempotently ensure the contributor-maintained staging tool and draft.

    An existing tool is reused only when the proof admin owns it; any other
    tool with the fixture slug stops the run before any write.
    """

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        tools: ToolRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        create_draft_tool: CreateDraftToolHandlerProtocol,
        update_tool_slug: UpdateToolSlugHandlerProtocol,
        assign_maintainer: AssignMaintainerHandlerProtocol,
        create_draft_version: CreateDraftVersionHandlerProtocol,
    ) -> None:
        self._uow = uow
        self._users = users
        self._tools = tools
        self._maintainers = maintainers
        self._versions = versions
        self._create_draft_tool = create_draft_tool
        self._update_tool_slug = update_tool_slug
        self._assign_maintainer = assign_maintainer
        self._create_draft_version = create_draft_version

    async def ensure(self, *, export: HuleEduSubjectExport) -> StagingProofFixtureResult:
        async with self._uow:
            admin = await self._imported_user(
                export=export, stable_account_key=STAGING_PROOF_ADMIN_KEY, role=Role.ADMIN
            )
            contributor = await self._imported_user(
                export=export,
                stable_account_key=STAGING_PROOF_CONTRIBUTOR_KEY,
                role=Role.CONTRIBUTOR,
            )

            tool = await self._tools.get_by_slug(slug=STAGING_PROOF_TOOL_SLUG)
            created_tool = tool is None
            if tool is None:
                new_tool = await self._create_draft_tool.handle(
                    actor=admin,
                    command=CreateDraftToolCommand(
                        title=STAGING_PROOF_TOOL_TITLE,
                        summary=STAGING_PROOF_TOOL_SUMMARY,
                    ),
                )
                renamed = await self._update_tool_slug.handle(
                    actor=admin,
                    command=UpdateToolSlugCommand(
                        tool_id=new_tool.tool.id, slug=STAGING_PROOF_TOOL_SLUG
                    ),
                )
                tool = renamed.tool
            elif tool.owner_user_id != admin.id:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="A tool with the staging proof slug is not owned by the proof admin",
                    details={"tool_slug": tool.slug, "tool_id": str(tool.id)},
                )

            assigned_maintainer = not await self._maintainers.is_maintainer(
                tool_id=tool.id, user_id=contributor.id
            )
            if assigned_maintainer:
                await self._assign_maintainer.handle(
                    actor=admin,
                    command=AssignMaintainerCommand(
                        tool_id=tool.id,
                        user_id=contributor.id,
                        reason="Hemma staging proof fixture",
                    ),
                )

            drafts = await self._versions.list_for_tool(
                tool_id=tool.id, states={VersionState.DRAFT}, limit=1
            )
            if drafts:
                draft = drafts[0]
                if draft.created_by_user_id != contributor.id:
                    raise DomainError(
                        code=ErrorCode.CONFLICT,
                        message="Staging proof tool draft was not created by the proof contributor",
                        details={"tool_slug": tool.slug, "draft_version_id": str(draft.id)},
                    )
                created_draft = False
            else:
                new_draft = await self._create_draft_version.handle(
                    actor=contributor,
                    command=CreateDraftVersionCommand(
                        tool_id=tool.id,
                        source_code=STAGING_PROOF_SOURCE_CODE,
                        change_summary="Hemma staging proof fixture",
                    ),
                )
                draft = new_draft.version
                created_draft = True

        return StagingProofFixtureResult(
            tool_id=tool.id,
            tool_slug=tool.slug,
            draft_version_id=draft.id,
            created_tool=created_tool,
            assigned_maintainer=assigned_maintainer,
            created_draft=created_draft,
        )

    async def _imported_user(
        self, *, export: HuleEduSubjectExport, stable_account_key: str, role: Role
    ) -> User:
        record = next(
            (item for item in export.accounts if item.stable_account_key == stable_account_key),
            None,
        )
        if record is None:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Staging proof account missing from the subject export",
                details={"stable_account_key": stable_account_key},
            )
        auth = await self._users.get_auth_by_email(record.email)
        if auth is None:
            raise DomainError(
                code=ErrorCode.NOT_FOUND,
                message="Staging proof account has not been imported",
                details={"stable_account_key": stable_account_key},
            )
        if auth.user.role is not role:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="Staging proof account does not hold its mapped role",
                details={
                    "stable_account_key": stable_account_key,
                    "expected_role": role.value,
                    "actual_role": auth.user.role.value,
                },
            )
        return auth.user
