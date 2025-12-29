"""Fixtures for RunSandboxHandler tests."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from tests.unit.application.scripting.handlers.sandbox_test_support import make_settings_mock


@pytest.fixture
def settings() -> Mock:
    return make_settings_mock()
