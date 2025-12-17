from __future__ import annotations

from skriptoteket.protocols.uow import UnitOfWorkProtocol


class FakeUow(UnitOfWorkProtocol):
    """Fake Unit of Work for unit tests.

    Tracks enter/exit states for verification.
    """

    def __init__(self) -> None:
        self.entered = False
        self.exited = False

    async def __aenter__(self) -> UnitOfWorkProtocol:
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.exited = True
