"""Adaptador de salida: API Socrata de datos.gov.co (JSON)."""
from typing import Callable, Optional

import requests

from domain.errors import ExternalServiceUnavailable
from domain.ports import OpenDataPort
from infrastructure.http.resilience import CircuitBreaker, retry_with_backoff

BASE_URL = "https://www.datos.gov.co/resource"


def _default_get(url: str, params: dict, timeout: float) -> list[dict]:
    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


class SocrataClient(OpenDataPort):
    def __init__(self, name: str, dataset_id: str,
                 breaker: Optional[CircuitBreaker] = None,
                 http_get: Callable[[str, dict, float], list[dict]] = _default_get,
                 max_attempts: int = 3, base_delay: float = 0.5,
                 sleep: Optional[Callable[[float], None]] = None,
                 timeout: float = 10.0):
        self.name = name
        self.dataset_id = dataset_id
        self.breaker = breaker or CircuitBreaker()
        self._get = http_get
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._sleep = sleep
        self._timeout = timeout

    def fetch_records(self, limit: int = 1000) -> list[dict]:
        url = f"{BASE_URL}/{self.dataset_id}.json"
        params = {"$limit": limit}
        kwargs = {"sleep": self._sleep} if self._sleep else {}

        def with_retry():
            return retry_with_backoff(
                lambda: self._get(url, params, self._timeout),
                max_attempts=self._max_attempts, base_delay=self._base_delay, **kwargs)

        try:
            return self.breaker.call(with_retry)
        except ExternalServiceUnavailable:
            raise
        except Exception as exc:
            raise ExternalServiceUnavailable(f"{self.name}: {exc}") from exc

    # --- utilidades para la demo del circuit breaker (video / sustentación) ---
    def simulate_outage(self):
        """Hace que todas las llamadas fallen, para ver CLOSED -> OPEN."""
        self._normal_get = getattr(self, "_normal_get", self._get)

        def _down(url, params, timeout):
            raise ConnectionError("Caída simulada de la API")
        self._get = _down

    def restore(self):
        if hasattr(self, "_normal_get"):
            self._get = self._normal_get
