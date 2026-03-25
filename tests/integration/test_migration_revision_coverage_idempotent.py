"""Revision-focused integration coverage for migrations that lacked explicit tests.

This module closes the gap between the older one-file-per-migration tests and
the newer migration chain by exercising each uncovered revision directly against
its parent revision and validating that reruns are safe no-ops.
"""

from __future__ import annotations

import pytest

from tests.integration.migration_idempotency_support import assert_revision_is_idempotent
from tests.integration.migration_schema_assertions import (
    COVERED_REVISION_IDS,
    SCHEMA_ASSERTIONS,
)


@pytest.mark.integration
@pytest.mark.docker
@pytest.mark.parametrize("revision_id", COVERED_REVISION_IDS, ids=COVERED_REVISION_IDS)
def test_uncovered_migration_revision_is_idempotent(postgres_container, revision_id: str) -> None:
    """Verify each uncovered revision upgrades cleanly and survives reruns."""
    assert_revision_is_idempotent(
        postgres_container=postgres_container,
        revision_id=revision_id,
        schema_assertion=SCHEMA_ASSERTIONS[revision_id],
    )
