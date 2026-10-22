"""Observe declared question output without admitting or validating produced items."""

from collections.abc import Awaitable, Callable, Mapping
from json import JSONDecoder
from typing import Literal

from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import QuestionFamily

QuestionReceiptObserver = Callable[[tuple[str, ...]], Awaitable[None]]


class DocxReceiptWriteError(Exception):
    """Carry a progress-port failure past the converter's content-fallback handlers."""

    def __init__(self, error: Exception) -> None:
        super().__init__(str(error))
        self.error = error


class CompletedItemsReader:
    """Read complete top-level ``items`` elements from incremental envelope text.

    JSONDecoder owns strings, escapes and nested values. This reader only walks the
    envelope's object members and the items array separators. Incomplete or malformed
    text yields no further observations; terminal response parsing remains authoritative.
    """

    def __init__(self) -> None:
        self._decoder = JSONDecoder()
        self._buffer = ""
        self._state: Literal[
            "root", "key", "colon", "value", "array", "item", "item_end", "member_end", "done"
        ] = "root"
        self._key = ""

    def feed(self, text: str) -> list[object]:
        """Return newly completed elements, even before the array or envelope closes."""
        if self._state == "done":
            return []
        self._buffer += text
        items: list[object] = []
        while self._state != "done":
            self._buffer = self._buffer.lstrip(" \t\r\n")
            if not self._buffer:
                break
            try:
                if not self._advance(items):
                    break
            except (ValueError, RecursionError):
                # This observer never turns a parsing issue into admission or retry policy.
                break
        return items

    def _take(self, token: str) -> None:
        if self._buffer.startswith(token):
            self._buffer = self._buffer[len(token) :]
        else:
            self._state = "done"

    def _advance(self, items: list[object]) -> bool:
        if self._state == "root":
            self._state = "key"
            self._take("{")
        elif self._state == "key":
            if self._buffer.startswith("}"):
                self._state = "done"
                return False
            key, end = self._decoder.raw_decode(self._buffer)
            if not isinstance(key, str):
                self._state = "done"
                return False
            self._key = key
            self._buffer = self._buffer[end:]
            self._state = "colon"
        elif self._state == "colon":
            self._state = "array" if self._key == "items" else "value"
            self._take(":")
        elif self._state == "array":
            self._state = "item"
            self._take("[")
        elif self._state in {"item", "value"}:
            if self._state == "item" and self._buffer.startswith("]"):
                self._buffer = self._buffer[1:]
                self._state = "member_end"
                return True
            value, end = self._decoder.raw_decode(self._buffer)
            # A number can continue in the next fragment; wait for its separator.
            if type(value) in {int, float} and (
                end == len(self._buffer) or self._buffer[end] not in " \t\r\n,]}"
            ):
                return False
            if self._state == "item":
                items.append(value)
                self._state = "item_end"
            else:
                self._state = "member_end"
            self._buffer = self._buffer[end:]
        elif self._state == "item_end":
            if self._buffer.startswith("]"):
                self._buffer = self._buffer[1:]
                self._state = "member_end"
            else:
                self._state = "item"
                self._take(",")
        elif self._state == "member_end":
            if self._buffer.startswith("}"):
                self._state = "done"
            else:
                self._state = "key"
                self._take(",")
        return True


class DocxOutputObserver:
    """Project item-declared question anchors to existing question identities."""

    def __init__(
        self,
        families: Mapping[str, QuestionFamily],
        on_received: QuestionReceiptObserver,
    ) -> None:
        self._reader = CompletedItemsReader()
        self._questions_by_anchor: dict[str, set[str]] = {}
        for family in families.values():
            for anchor in family.question_anchors:
                self._questions_by_anchor.setdefault(anchor, set()).add(family.question_id)
        self._on_received = on_received

    async def on_text(self, text: str) -> None:
        """Notify once per fragment for every addressed question, irrespective of outcome."""
        question_ids: set[str] = set()
        for item in self._reader.feed(text):
            if not isinstance(item, dict):
                continue
            anchors = item.get("source_anchors")
            if isinstance(anchors, list):
                for anchor in anchors:
                    if isinstance(anchor, str):
                        question_ids.update(self._questions_by_anchor.get(anchor, ()))
        if question_ids:
            try:
                await self._on_received(tuple(sorted(question_ids)))
            except Exception as error:
                raise DocxReceiptWriteError(error) from error
