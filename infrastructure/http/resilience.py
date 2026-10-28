"""Circuit breaker (3 estados) y retry con backoff exponencial."""
import random
import time
from enum import Enum
from typing import Callable, TypeVar

from domain.errors import ExternalServiceUnavailable

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"        # funciona normal
    OPEN = "OPEN"            # bloquea llamadas (falló demasiado)
    HALF_OPEN = "HALF_OPEN"  # deja pasar UNA llamada de prueba


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0,
                 clock: Callable[[], float] = time.monotonic):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._clock = clock
        self._failures = 0
        self._opened_at = 0.0
        self._state = CircuitState.CLOSED

    @property
    def state(self) -> CircuitState:
        # OPEN pasa solo a HALF_OPEN cuando vence el tiempo de recuperación
        if (self._state is CircuitState.OPEN
                and self._clock() - self._opened_at >= self.recovery_timeout):
            self._state = CircuitState.HALF_OPEN
        return self._state

    def call(self, func: Callable[[], T]) -> T:
        if self.state is CircuitState.OPEN:
            raise ExternalServiceUnavailable("Circuit breaker abierto: API temporalmente bloqueada.")
        try:
            result = func()
        except Exception:
            self._on_failure()
            raise
        self._on_success()
        return result

    def _on_success(self):
        self._failures = 0
        self._state = CircuitState.CLOSED

    def _on_failure(self):
        self._failures += 1
        if self._state is CircuitState.HALF_OPEN or self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = self._clock()


def retry_with_backoff(func: Callable[[], T], max_attempts: int = 3, base_delay: float = 0.5,
                       max_delay: float = 8.0, jitter: bool = True,
                       sleep: Callable[[float], None] = time.sleep,
                       retry_on: tuple = (Exception,)) -> T:
    """Reintenta con esperas 0.5s, 1s, 2s, 4s... (+ jitter). Relanza el último error."""
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return func()
        except ExternalServiceUnavailable:
            raise  # circuito abierto: no tiene sentido reintentar
        except retry_on as exc:
            last_exc = exc
            if attempt == max_attempts - 1:
                break
            delay = min(max_delay, base_delay * (2 ** attempt))
            if jitter:
                delay += random.uniform(0, delay * 0.1)
            sleep(delay)
    raise last_exc
