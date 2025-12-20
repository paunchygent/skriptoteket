from __future__ import annotations

from collections.abc import Mapping

class Resource:
    @classmethod
    def create(cls, attributes: Mapping[str, str]) -> Resource: ...
