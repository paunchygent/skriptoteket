from __future__ import annotations

import secrets

from skriptoteket.protocols.token_generator import TokenGeneratorProtocol


class SecureTokenGenerator(TokenGeneratorProtocol):
    def new_token(self) -> str:
        return secrets.token_urlsafe(32)
