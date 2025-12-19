"""Unit tests for logging redaction processor."""

from __future__ import annotations

import pytest

from skriptoteket.observability.logging import (
    _REDACTED,
    _redact_sensitive_data,
    _redact_value,
)


class TestRedactValue:
    """Tests for the _redact_value helper function."""

    def test_simple_string_unchanged(self) -> None:
        assert _redact_value("hello") == "hello"

    def test_number_unchanged(self) -> None:
        assert _redact_value(42) == 42

    def test_none_unchanged(self) -> None:
        assert _redact_value(None) is None

    def test_dict_with_sensitive_key_redacted(self) -> None:
        result = _redact_value({"password": "secret123", "user": "alice"})
        assert result == {"password": _REDACTED, "user": "alice"}

    def test_nested_dict_redacted(self) -> None:
        result = _redact_value({"outer": {"api_key": "key123", "name": "test"}})
        assert result == {"outer": {"api_key": _REDACTED, "name": "test"}}

    def test_list_with_dicts_redacted(self) -> None:
        result = _redact_value([{"token": "abc"}, {"value": 123}])
        assert result == [{"token": _REDACTED}, {"value": 123}]

    def test_deeply_nested_redacted(self) -> None:
        result = _redact_value({"a": {"b": {"c": {"secret": "shhh"}}}})
        assert result == {"a": {"b": {"c": {"secret": _REDACTED}}}}


class TestRedactSensitiveData:
    """Tests for the structlog processor _redact_sensitive_data."""

    def test_password_redacted(self) -> None:
        event_dict = {"event": "login", "password": "secret123"}
        result = _redact_sensitive_data(None, "info", event_dict)
        assert result["password"] == _REDACTED
        assert result["event"] == "login"

    def test_token_redacted(self) -> None:
        event_dict = {"event": "auth", "token": "bearer-xyz"}
        result = _redact_sensitive_data(None, "info", event_dict)
        assert result["token"] == _REDACTED

    def test_api_key_redacted(self) -> None:
        event_dict = {"api_key": "key-12345", "status": "ok"}
        result = _redact_sensitive_data(None, "info", event_dict)
        assert result["api_key"] == _REDACTED
        assert result["status"] == "ok"

    def test_authorization_redacted(self) -> None:
        event_dict = {"authorization": "Bearer xyz", "path": "/api"}
        result = _redact_sensitive_data(None, "info", event_dict)
        assert result["authorization"] == _REDACTED

    def test_credential_redacted(self) -> None:
        event_dict = {"user_credential": "secret", "user_id": 42}
        result = _redact_sensitive_data(None, "info", event_dict)
        assert result["user_credential"] == _REDACTED

    def test_session_redacted(self) -> None:
        event_dict = {"session_id": "abc123", "user": "bob"}
        result = _redact_sensitive_data(None, "info", event_dict)
        assert result["session_id"] == _REDACTED

    def test_cookie_redacted(self) -> None:
        event_dict = {"cookie": "session=abc", "path": "/"}
        result = _redact_sensitive_data(None, "info", event_dict)
        assert result["cookie"] == _REDACTED

    def test_bearer_redacted(self) -> None:
        event_dict = {"bearer_token": "xyz123"}
        result = _redact_sensitive_data(None, "info", event_dict)
        assert result["bearer_token"] == _REDACTED

    def test_secret_redacted(self) -> None:
        event_dict = {"client_secret": "shhh", "client_id": "app1"}
        result = _redact_sensitive_data(None, "info", event_dict)
        assert result["client_secret"] == _REDACTED
        assert result["client_id"] == "app1"

    def test_case_insensitive_redaction(self) -> None:
        event_dict = {"PASSWORD": "upper", "Token": "mixed", "API_KEY": "caps"}
        result = _redact_sensitive_data(None, "info", event_dict)
        assert result["PASSWORD"] == _REDACTED
        assert result["Token"] == _REDACTED
        assert result["API_KEY"] == _REDACTED

    def test_partial_match_redacted(self) -> None:
        event_dict = {"password_hash": "hashed", "reset_token": "xyz"}
        result = _redact_sensitive_data(None, "info", event_dict)
        assert result["password_hash"] == _REDACTED
        assert result["reset_token"] == _REDACTED

    def test_non_sensitive_keys_unchanged(self) -> None:
        event_dict = {
            "event": "request",
            "user_id": 123,
            "path": "/api/users",
            "method": "GET",
            "status_code": 200,
        }
        result = _redact_sensitive_data(None, "info", event_dict)
        assert result == event_dict

    def test_nested_dict_in_event_redacted(self) -> None:
        event_dict = {
            "event": "auth_attempt",
            "data": {"password": "secret", "username": "alice"},
        }
        result = _redact_sensitive_data(None, "info", event_dict)
        assert result["event"] == "auth_attempt"
        assert result["data"]["password"] == _REDACTED
        assert result["data"]["username"] == "alice"

    def test_list_in_event_redacted(self) -> None:
        event_dict = {
            "event": "batch",
            "items": [{"token": "abc"}, {"name": "test"}],
        }
        result = _redact_sensitive_data(None, "info", event_dict)
        assert result["items"][0]["token"] == _REDACTED
        assert result["items"][1]["name"] == "test"

    def test_already_redacted_unchanged(self) -> None:
        event_dict = {"password": _REDACTED, "event": "test"}
        result = _redact_sensitive_data(None, "info", event_dict)
        assert result["password"] == _REDACTED


@pytest.mark.unit
class TestRedactionIntegration:
    """Integration-style tests verifying redaction behavior."""

    def test_typical_login_event(self) -> None:
        """Simulate a typical login log event."""
        event_dict = {
            "event": "User login attempt",
            "email": "user@example.com",
            "password": "supersecret",
            "correlation_id": "abc-123",
            "timestamp": "2025-01-01T00:00:00Z",
        }
        result = _redact_sensitive_data(None, "info", event_dict)

        assert result["password"] == _REDACTED
        assert result["email"] == "user@example.com"
        assert result["correlation_id"] == "abc-123"

    def test_api_request_with_auth_header(self) -> None:
        """Simulate API request logging with auth headers."""
        event_dict = {
            "event": "API request",
            "path": "/api/v1/tools",
            "method": "POST",
            "headers": {
                "authorization": "Bearer eyJ...",
                "content-type": "application/json",
                "x-api-key": "secret-key-123",
            },
        }
        result = _redact_sensitive_data(None, "info", event_dict)

        assert result["headers"]["authorization"] == _REDACTED
        assert result["headers"]["x-api-key"] == _REDACTED
        assert result["headers"]["content-type"] == "application/json"
