"""Unit tests for logging redaction processor."""

from __future__ import annotations

import pytest

from skriptoteket.observability.redaction import REDACTED, redact_sensitive_data, redact_value


class TestRedactValue:
    """Tests for the _redact_value helper function."""

    def test_simple_string_unchanged(self) -> None:
        assert redact_value("hello") == "hello"

    def test_number_unchanged(self) -> None:
        assert redact_value(42) == 42

    def test_none_unchanged(self) -> None:
        assert redact_value(None) is None

    def test_dict_with_sensitive_key_redacted(self) -> None:
        result = redact_value({"password": "secret123", "user": "alice"})
        assert result == {"password": REDACTED, "user": "alice"}

    def test_nested_dict_redacted(self) -> None:
        result = redact_value({"outer": {"api_key": "key123", "name": "test"}})
        assert result == {"outer": {"api_key": REDACTED, "name": "test"}}

    def test_list_with_dicts_redacted(self) -> None:
        result = redact_value([{"token": "abc"}, {"value": 123}])
        assert result == [{"token": REDACTED}, {"value": 123}]

    def test_deeply_nested_redacted(self) -> None:
        result = redact_value({"a": {"b": {"c": {"secret": "shhh"}}}})
        assert result == {"a": {"b": {"c": {"secret": REDACTED}}}}


class TestRedactSensitiveData:
    """Tests for the structlog processor _redact_sensitive_data."""

    def test_password_redacted(self) -> None:
        event_dict = {"event": "login", "password": "secret123"}
        result = redact_sensitive_data(None, "info", event_dict)
        assert result["password"] == REDACTED
        assert result["event"] == "login"

    def test_token_redacted(self) -> None:
        event_dict = {"event": "auth", "token": "bearer-xyz"}
        result = redact_sensitive_data(None, "info", event_dict)
        assert result["token"] == REDACTED

    def test_api_key_redacted(self) -> None:
        event_dict = {"api_key": "key-12345", "status": "ok"}
        result = redact_sensitive_data(None, "info", event_dict)
        assert result["api_key"] == REDACTED
        assert result["status"] == "ok"

    def test_authorization_redacted(self) -> None:
        event_dict = {"authorization": "Bearer xyz", "path": "/api"}
        result = redact_sensitive_data(None, "info", event_dict)
        assert result["authorization"] == REDACTED

    def test_credential_redacted(self) -> None:
        event_dict = {"user_credential": "secret", "user_id": 42}
        result = redact_sensitive_data(None, "info", event_dict)
        assert result["user_credential"] == REDACTED

    def test_session_redacted(self) -> None:
        event_dict = {"session_id": "abc123", "user": "bob"}
        result = redact_sensitive_data(None, "info", event_dict)
        assert result["session_id"] == REDACTED

    def test_cookie_redacted(self) -> None:
        event_dict = {"cookie": "session=abc", "path": "/"}
        result = redact_sensitive_data(None, "info", event_dict)
        assert result["cookie"] == REDACTED

    def test_bearer_redacted(self) -> None:
        event_dict = {"bearer_token": "xyz123"}
        result = redact_sensitive_data(None, "info", event_dict)
        assert result["bearer_token"] == REDACTED

    def test_secret_redacted(self) -> None:
        event_dict = {"client_secret": "shhh", "client_id": "app1"}
        result = redact_sensitive_data(None, "info", event_dict)
        assert result["client_secret"] == REDACTED
        assert result["client_id"] == "app1"

    def test_case_insensitive_redaction(self) -> None:
        event_dict = {"PASSWORD": "upper", "Token": "mixed", "API_KEY": "caps"}
        result = redact_sensitive_data(None, "info", event_dict)
        assert result["PASSWORD"] == REDACTED
        assert result["Token"] == REDACTED
        assert result["API_KEY"] == REDACTED

    def test_partial_match_redacted(self) -> None:
        event_dict = {"password_hash": "hashed", "reset_token": "xyz"}
        result = redact_sensitive_data(None, "info", event_dict)
        assert result["password_hash"] == REDACTED
        assert result["reset_token"] == REDACTED

    def test_non_sensitive_keys_unchanged(self) -> None:
        event_dict = {
            "event": "request",
            "user_id": 123,
            "path": "/api/users",
            "method": "GET",
            "status_code": 200,
        }
        result = redact_sensitive_data(None, "info", event_dict)
        assert result == event_dict

    def test_nested_dict_in_event_redacted(self) -> None:
        event_dict = {
            "event": "auth_attempt",
            "data": {"password": "secret", "username": "alice"},
        }
        result = redact_sensitive_data(None, "info", event_dict)
        assert result["event"] == "auth_attempt"
        assert result["data"]["password"] == REDACTED
        assert result["data"]["username"] == "alice"

    def test_list_in_event_redacted(self) -> None:
        event_dict = {
            "event": "batch",
            "items": [{"token": "abc"}, {"name": "test"}],
        }
        result = redact_sensitive_data(None, "info", event_dict)
        assert result["items"][0]["token"] == REDACTED
        assert result["items"][1]["name"] == "test"

    def test_already_redacted_unchanged(self) -> None:
        event_dict = {"password": REDACTED, "event": "test"}
        result = redact_sensitive_data(None, "info", event_dict)
        assert result["password"] == REDACTED

    def test_token_counts_and_tokenizer_not_redacted(self) -> None:
        event_dict = {
            "message_tokens": 123,
            "context_window_tokens": 456,
            "max_output_tokens": 789,
            "tokenizer": "tekken",
        }
        result = redact_sensitive_data(None, "info", event_dict)
        assert result == event_dict


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
        result = redact_sensitive_data(None, "info", event_dict)

        assert result["password"] == REDACTED
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
        result = redact_sensitive_data(None, "info", event_dict)

        assert result["headers"]["authorization"] == REDACTED
        assert result["headers"]["x-api-key"] == REDACTED
        assert result["headers"]["content-type"] == "application/json"
