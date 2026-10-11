from __future__ import annotations

import typer

from skriptoteket.application.catalog.commands import PublishToolCommand, UpdateToolMetadataCommand
from skriptoteket.application.catalog.handlers.publish_tool import PublishToolHandler
from skriptoteket.application.catalog.handlers.update_tool_metadata import UpdateToolMetadataHandler
from skriptoteket.application.scripting.commands import (
    CreateDraftVersionCommand,
    PublishVersionCommand,
    SubmitForReviewCommand,
)
from skriptoteket.application.scripting.draft_locks import AcquireDraftLockCommand
from skriptoteket.application.scripting.handlers.acquire_draft_lock import (
    AcquireDraftLockHandler,
)
from skriptoteket.application.scripting.handlers.create_draft_version import (
    CreateDraftVersionHandler,
)
from skriptoteket.application.scripting.handlers.publish_version import PublishVersionHandler
from skriptoteket.application.scripting.handlers.submit_for_review import SubmitForReviewHandler
from skriptoteket.domain.catalog.models import Tool, update_tool_metadata
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.repositories.category_repository import (
    PostgreSQLCategoryRepository,
)
from skriptoteket.infrastructure.repositories.profession_repository import (
    PostgreSQLProfessionRepository,
)
from skriptoteket.infrastructure.repositories.tool_repository import PostgreSQLToolRepository
from skriptoteket.infrastructure.repositories.tool_version_repository import (
    PostgreSQLToolVersionRepository,
)
from skriptoteket.script_bank.sources import read_script_bank_source


def _normalize_seed_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.split()).casefold()


async def _find_tool_by_title_summary(
    *,
    tools: PostgreSQLToolRepository,
    title: str,
    summary: str | None,
) -> Tool | None:
    normalized_title = _normalize_seed_text(title)
    normalized_summary = _normalize_seed_text(summary)

    if not normalized_title:
        return None

    candidates = await tools.list_all()
    matches = [
        candidate
        for candidate in candidates
        if _normalize_seed_text(candidate.title) == normalized_title
        and _normalize_seed_text(candidate.summary) == normalized_summary
    ]

    if len(matches) > 1:
        slugs = ", ".join(sorted({candidate.slug for candidate in matches}))
        raise SystemExit(
            "Duplicate tools found with matching title+summary. "
            f"Resolve duplicates before seeding. Slugs: {slugs}"
        )

    return matches[0] if matches else None


async def seed_one_entry(
    *,
    actor,
    entry,
    uow: SQLAlchemyUnitOfWork,
    tools: PostgreSQLToolRepository,
    versions: PostgreSQLToolVersionRepository,
    professions: PostgreSQLProfessionRepository,
    categories: PostgreSQLCategoryRepository,
    create_draft_version: CreateDraftVersionHandler,
    acquire_draft_lock: AcquireDraftLockHandler,
    submit_for_review: SubmitForReviewHandler,
    publish_version: PublishVersionHandler,
    publish_tool: PublishToolHandler,
    update_tool_metadata_handler: UpdateToolMetadataHandler,
    sync_metadata: bool,
    sync_code: bool,
    publish: bool,
    dry_run: bool,
) -> None:
    now = UTCClock().now()
    tool = await tools.get_by_slug(slug=entry.slug)
    created = False
    deduped_from_slug: str | None = None

    if tool is None:
        dedupe_match = await _find_tool_by_title_summary(
            tools=tools,
            title=entry.title,
            summary=entry.summary,
        )
        if dedupe_match is not None:
            tool = dedupe_match
            deduped_from_slug = entry.slug
            typer.echo(f"Seed dedupe: using existing tool '{tool.slug}' for entry '{entry.slug}'.")
        else:
            tool = None

    if tool is None:
        profession_ids = []
        for profession_slug in entry.profession_slugs:
            profession = await professions.get_by_slug(profession_slug)
            if profession is None:
                raise SystemExit(f"Unknown profession slug: {profession_slug}")
            profession_ids.append(profession.id)

        category_ids = []
        for category_slug in entry.category_slugs:
            category = await categories.get_by_slug(category_slug)
            if category is None:
                raise SystemExit(f"Unknown category slug: {category_slug}")
            category_ids.append(category.id)

        draft_tool = Tool(
            id=UUID4Generator().new_uuid(),
            owner_user_id=actor.id,
            slug=entry.slug,
            title=entry.title,
            summary=entry.summary,
            is_published=False,
            active_version_id=None,
            created_at=now,
            updated_at=now,
        )
        normalized_tool = update_tool_metadata(
            tool=draft_tool,
            title=draft_tool.title,
            summary=draft_tool.summary,
            now=now,
        )

        if dry_run:
            typer.echo(f"[dry-run] Create tool: {entry.slug}")
        else:
            async with uow:
                tool = await tools.create_draft(
                    tool=normalized_tool,
                    profession_ids=profession_ids,
                    category_ids=category_ids,
                )
            created = True
    else:
        if sync_metadata and (tool.title != entry.title or tool.summary != entry.summary):
            if dry_run:
                typer.echo(f"[dry-run] Update metadata: {entry.slug}")
            else:
                await update_tool_metadata_handler.handle(
                    actor=actor,
                    command=UpdateToolMetadataCommand(
                        tool_id=tool.id,
                        title=entry.title,
                        summary=entry.summary,
                    ),
                )
                tool = await tools.get_by_id(tool_id=tool.id)
                if tool is None:
                    raise SystemExit(f"Tool disappeared during seed: {entry.slug}")

    assert tool is not None

    source_code, bundle_files = read_script_bank_source(source_filename=entry.source_filename)

    active_version = await versions.get_active_for_tool(tool_id=tool.id)
    if active_version is None:
        if dry_run:
            typer.echo(f"[dry-run] Create + publish initial version: {entry.slug}")
        else:
            await _acquire_seed_draft_lock(
                actor=actor,
                tool_slug=tool.slug,
                tool_id=tool.id,
                versions=versions,
                acquire_draft_lock=acquire_draft_lock,
                dry_run=dry_run,
            )
            draft_result = await create_draft_version.handle(
                actor=actor,
                command=CreateDraftVersionCommand(
                    tool_id=tool.id,
                    entrypoint=entry.entrypoint,
                    source_code=source_code,
                    bundle_files=bundle_files,
                    settings_schema=entry.settings_schema,
                    input_schema=entry.input_schema,
                    usage_instructions=entry.usage_instructions,
                    change_summary="Seed: initial version från repo",
                ),
            )
            submitted = await submit_for_review.handle(
                actor=actor,
                command=SubmitForReviewCommand(
                    version_id=draft_result.version.id,
                    review_note="Automatiskt seedad från repo script bank.",
                ),
            )
            await publish_version.handle(
                actor=actor,
                command=PublishVersionCommand(
                    version_id=submitted.version.id,
                    change_summary="Automatiskt publicerad från repo script bank.",
                ),
            )
    elif sync_code and (
        active_version.entrypoint != entry.entrypoint
        or active_version.source_code != source_code
        or active_version.bundle_files != bundle_files
        or active_version.usage_instructions != entry.usage_instructions
        or active_version.settings_schema != entry.settings_schema
        or active_version.input_schema != entry.input_schema
    ):
        if dry_run:
            typer.echo(f"[dry-run] Create + publish updated version: {entry.slug}")
        else:
            await _acquire_seed_draft_lock(
                actor=actor,
                tool_slug=tool.slug,
                tool_id=tool.id,
                versions=versions,
                acquire_draft_lock=acquire_draft_lock,
                dry_run=dry_run,
            )
            draft_result = await create_draft_version.handle(
                actor=actor,
                command=CreateDraftVersionCommand(
                    tool_id=tool.id,
                    derived_from_version_id=active_version.id,
                    entrypoint=entry.entrypoint,
                    source_code=source_code,
                    bundle_files=bundle_files,
                    settings_schema=entry.settings_schema,
                    input_schema=entry.input_schema,
                    usage_instructions=entry.usage_instructions,
                    change_summary="Seed: uppdaterad version från repo",
                ),
            )
            submitted = await submit_for_review.handle(
                actor=actor,
                command=SubmitForReviewCommand(
                    version_id=draft_result.version.id,
                    review_note="Automatiskt uppdaterad från repo script bank.",
                ),
            )
            await publish_version.handle(
                actor=actor,
                command=PublishVersionCommand(
                    version_id=submitted.version.id,
                    change_summary="Automatiskt publicerad (uppdatering) från repo script bank.",
                ),
            )

    tool = await tools.get_by_id(tool_id=tool.id)
    if tool is None:
        raise SystemExit(f"Tool disappeared during seed: {entry.slug}")

    if publish and not tool.is_published:
        if dry_run:
            typer.echo(f"[dry-run] Publish tool: {tool.slug}")
        else:
            await publish_tool.handle(actor=actor, command=PublishToolCommand(tool_id=tool.id))

    if created and not dry_run:
        typer.echo(f"Seeded tool: {entry.slug} (created)")
    elif deduped_from_slug and not dry_run:
        typer.echo(f"Seeded tool: {tool.slug} (deduped from {deduped_from_slug})")
    elif not dry_run:
        typer.echo(f"Seeded tool: {entry.slug} (updated)")


async def _acquire_seed_draft_lock(
    *,
    actor,
    tool_slug: str,
    tool_id,
    versions: PostgreSQLToolVersionRepository,
    acquire_draft_lock: AcquireDraftLockHandler,
    dry_run: bool,
) -> None:
    draft_versions = await versions.list_for_tool(
        tool_id=tool_id,
        states={VersionState.DRAFT},
        limit=1,
    )
    if not draft_versions:
        return

    draft_head = draft_versions[0]
    if dry_run:
        typer.echo(f"[dry-run] Acquire draft lock: {tool_slug}")
        return

    await acquire_draft_lock.handle(
        actor=actor,
        command=AcquireDraftLockCommand(
            tool_id=tool_id,
            draft_head_id=draft_head.id,
            force=False,
        ),
    )
