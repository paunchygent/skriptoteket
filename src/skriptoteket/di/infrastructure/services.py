"""Infrastructure provider: core services (clock, IDs, tokens, email, sleeping)."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.config import Settings
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.email.sender_factory import create_email_sender
from skriptoteket.infrastructure.email.template_renderer import Jinja2EmailTemplateRenderer
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.security.password_hasher import Argon2PasswordHasher
from skriptoteket.infrastructure.time.asyncio_sleeper import AsyncioSleeper
from skriptoteket.infrastructure.token_generator import SecureTokenGenerator
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.email import EmailSenderProtocol, EmailTemplateRendererProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import PasswordHasherProtocol
from skriptoteket.protocols.sleeper import SleeperProtocol
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol


class InfrastructureServicesProvider(Provider):
    """Provides shared infrastructure services."""

    @provide(scope=Scope.APP)
    def clock(self) -> ClockProtocol:
        return UTCClock()

    @provide(scope=Scope.APP)
    def sleeper(self) -> SleeperProtocol:
        return AsyncioSleeper()

    @provide(scope=Scope.APP)
    def id_generator(self) -> IdGeneratorProtocol:
        return UUID4Generator()

    @provide(scope=Scope.APP)
    def token_generator(self) -> TokenGeneratorProtocol:
        return SecureTokenGenerator()

    @provide(scope=Scope.APP)
    def password_hasher(self) -> PasswordHasherProtocol:
        return Argon2PasswordHasher()

    @provide(scope=Scope.APP)
    def email_sender(self, settings: Settings) -> EmailSenderProtocol:
        return create_email_sender(settings)

    @provide(scope=Scope.APP)
    def email_template_renderer(self) -> EmailTemplateRendererProtocol:
        return Jinja2EmailTemplateRenderer()
