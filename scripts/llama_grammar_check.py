from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8082/v1"

_GRAMMAR = r"""
root ::= ws "{" ws "\"ok\"" ws ":" ws ("true" | "false") ws "}" ws
ws ::= [ \t\n\r]*
""".strip()


def _get_model_id(client: httpx.Client, base_url: str) -> str:
    response = client.get(f"{base_url}/models")
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Expected /models response to be an object")
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise ValueError("No models returned from /models")
    model_id = data[0].get("id")
    if not isinstance(model_id, str) or not model_id:
        raise ValueError("Model id missing in /models response")
    return model_id


def _extract_chat_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Chat response missing choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError("Chat response missing message")
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("Chat response content is not a string")
    return content


def _extract_completion_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Completion response missing choices")
    text = choices[0].get("text")
    if not isinstance(text, str):
        raise ValueError("Completion response text is not a string")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify llama.cpp grammar + json_schema behavior.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    client = httpx.Client(timeout=30.0)
    try:
        model_id = _get_model_id(client, args.base_url)

        chat_payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": "Return JSON with a boolean ok."}],
            "grammar": _GRAMMAR,
            "temperature": 0,
            "max_tokens": 64,
        }
        chat_response = client.post(f"{args.base_url}/chat/completions", json=chat_payload)
        chat_response.raise_for_status()
        chat_json = chat_response.json()
        chat_content = _extract_chat_content(chat_json)
        try:
            chat_value = json.loads(chat_content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Chat grammar output is not JSON: {exc}") from exc
        if not isinstance(chat_value, dict) or "ok" not in chat_value:
            raise ValueError("Chat grammar output missing ok field")

        completion_payload = {
            "model": model_id,
            "prompt": "Return JSON with a boolean ok.",
            "json_schema": {
                "type": "object",
                "properties": {"ok": {"type": "boolean"}},
                "required": ["ok"],
                "additionalProperties": False,
            },
            "temperature": 0,
            "max_tokens": 64,
        }
        completion_response = client.post(f"{args.base_url}/completions", json=completion_payload)
        completion_response.raise_for_status()
        completion_json = completion_response.json()
        completion_text = _extract_completion_text(completion_json)
        try:
            completion_value = json.loads(completion_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Completion json_schema output is not JSON: {exc}") from exc
        if not isinstance(completion_value, dict) or "ok" not in completion_value:
            raise ValueError("Completion json_schema output missing ok field")

        print("ok: chat grammar and completion json_schema both enforced JSON")
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI diagnostics
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
