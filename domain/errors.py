"""Errores del dominio (no dependen de ningún framework)."""


class DomainError(Exception):
    """Error base de las reglas de negocio."""


class GroupNotFound(DomainError):
    """El grupo solicitado no existe."""


class ExternalServiceUnavailable(DomainError):
    """Una API externa no respondió (o el circuit breaker está abierto)."""
