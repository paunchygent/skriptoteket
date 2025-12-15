import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from skriptoteket.infrastructure.runner.retention import prune_artifacts_root


def test_prune_artifacts_root_deletes_old_run_dirs(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    old_dir = tmp_path / str(uuid4())
    new_dir = tmp_path / str(uuid4())

    old_dir.mkdir()
    new_dir.mkdir()

    old_mtime = (now - timedelta(days=10)).timestamp()
    os.utime(old_dir, (old_mtime, old_mtime))

    deleted = prune_artifacts_root(artifacts_root=tmp_path, retention_days=7, now=now)

    assert deleted == 1
    assert not old_dir.exists()
    assert new_dir.exists()


def test_prune_artifacts_root_with_nonexistent_dir_returns_zero(tmp_path) -> None:
    nonexistent = tmp_path / "does_not_exist"

    deleted = prune_artifacts_root(
        artifacts_root=nonexistent,
        retention_days=7,
        now=datetime.now(timezone.utc),
    )

    assert deleted == 0


def test_prune_artifacts_root_skips_non_uuid_directories(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    non_uuid_dir = tmp_path / "not-a-uuid"
    non_uuid_dir.mkdir()

    old_mtime = (now - timedelta(days=10)).timestamp()
    os.utime(non_uuid_dir, (old_mtime, old_mtime))

    deleted = prune_artifacts_root(artifacts_root=tmp_path, retention_days=7, now=now)

    assert deleted == 0
    assert non_uuid_dir.exists()


def test_prune_artifacts_root_skips_files(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    file_path = tmp_path / str(uuid4())
    file_path.write_text("not a directory")

    old_mtime = (now - timedelta(days=10)).timestamp()
    os.utime(file_path, (old_mtime, old_mtime))

    deleted = prune_artifacts_root(artifacts_root=tmp_path, retention_days=7, now=now)

    assert deleted == 0
    assert file_path.exists()


def test_prune_artifacts_root_with_negative_retention_raises_value_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="retention_days must be >= 0"):
        prune_artifacts_root(
            artifacts_root=tmp_path,
            retention_days=-1,
            now=datetime.now(timezone.utc),
        )


def test_prune_artifacts_root_with_naive_datetime_raises_value_error(tmp_path) -> None:
    naive_now = datetime.now()  # No timezone

    with pytest.raises(ValueError, match="now must be timezone-aware"):
        prune_artifacts_root(
            artifacts_root=tmp_path,
            retention_days=7,
            now=naive_now,
        )


def test_prune_artifacts_root_with_zero_retention_deletes_old_dirs(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    run_dir = tmp_path / str(uuid4())
    run_dir.mkdir()

    # Set mtime to 1 second in the past (older than cutoff at now)
    old_mtime = (now - timedelta(seconds=1)).timestamp()
    os.utime(run_dir, (old_mtime, old_mtime))

    deleted = prune_artifacts_root(artifacts_root=tmp_path, retention_days=0, now=now)

    assert deleted == 1
    assert not run_dir.exists()
