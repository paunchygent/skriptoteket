"""Unit tests for scripts/hemma_deploy_config.py.

Purpose:
    Prove that the deploy workers' configuration reader parses `.env` the way
    python-dotenv does (quotes and inline comments) and prints only the names
    the caller asks for.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.hemma_deploy_config import main, read_config


def test_inline_comment_and_quotes_are_not_part_of_the_value(tmp_path: Path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        'HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_DIR="/fixture/identity" # shared config\n',
        encoding="utf-8",
    )

    config = read_config(dotenv_path, ["HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_DIR"])

    assert config == {"HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_DIR": "/fixture/identity"}


def test_prints_only_requested_set_names(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "BOOTSTRAP_SUPERUSER_EMAIL=admin@example.com\n"
        "SECRET_KEY=not-requested\n"
        "SIR_CONVERT_A_LOT_V2_BASE_URL=\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            str(dotenv_path),
            "BOOTSTRAP_SUPERUSER_EMAIL",
            "SIR_CONVERT_A_LOT_V2_BASE_URL",
            "HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_DIR",
        ]
    )

    assert exit_code == 0
    assert capsys.readouterr().out == "BOOTSTRAP_SUPERUSER_EMAIL=admin@example.com\n"
