from __future__ import annotations

from uuid import UUID, uuid4

from skriptoteket.protocols.id_generator import IdGeneratorProtocol


class UUID4Generator(IdGeneratorProtocol):
    def new_uuid(self) -> UUID:
        return uuid4()
