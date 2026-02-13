from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any


class LlamaClientError(RuntimeError):
    pass


def wait_for_health(
    *,
    base_url: str,
    timeout_seconds: float,
    interval_seconds: float = 2.0,
) -> None:
    url = base_url.rstrip("/") + "/health"
    deadline = time.time() + timeout_seconds
    last_error: str | None = None

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=min(interval_seconds, 5.0)) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict) and payload.get("status") == "ok":
                return
            last_error = f"unexpected health payload: {payload}"
        except Exception as exc:  # noqa: BLE001 - keep retry loop simple
            last_error = f"{type(exc).__name__}: {exc}"

        time.sleep(interval_seconds)

    raise LlamaClientError(f"Health check timed out ({timeout_seconds}s): {last_error}")


def send_chat_completion(
    *,
    prompt: str,
    base_url: str,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout_seconds: float,
    system_prompt: str | None = None,
) -> bytes:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    url = base_url.rstrip("/") + "/v1/chat/completions"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        error_body = exc.read()
        detail = error_body.decode("utf-8", errors="replace") if error_body else ""
        raise LlamaClientError(f"HTTP {exc.code} {exc.reason}: {detail}") from exc
    except Exception as exc:  # noqa: BLE001
        raise LlamaClientError(f"{type(exc).__name__}: {exc}") from exc


def extract_text(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    return content if isinstance(content, str) else ""


def extract_usage(response_json: dict[str, Any]) -> dict[str, Any]:
    usage = response_json.get("usage") or {}
    timings = response_json.get("timings") or {}
    finish_reason = None
    if response_json.get("choices"):
        finish_reason = response_json["choices"][0].get("finish_reason")
    return {
        "completion_tokens": usage.get("completion_tokens"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "predicted_per_second": timings.get("predicted_per_second"),
        "predicted_per_token_ms": timings.get("predicted_per_token_ms"),
        "predicted_ms": timings.get("predicted_ms"),
        "finish_reason": finish_reason,
    }
