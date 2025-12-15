import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

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
