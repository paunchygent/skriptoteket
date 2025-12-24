from __future__ import annotations


class ToolUserError(Exception):
    """A safe, user-facing error raised by tool scripts.

    The message is returned as `error_summary` in the runner result contract and
    MUST be safe for end-user display (no stack traces, no host paths, no secrets).
    """

    def __init__(self, message: str) -> None:
        safe_message = message.strip() or "Ett fel inträffade."
        super().__init__(safe_message)
        self.safe_message = safe_message
