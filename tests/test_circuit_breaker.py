import pytest

from domain.errors import ExternalServiceUnavailable
from infrastructure.http.resilience import CircuitBreaker, CircuitState, retry_with_backoff


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def boom():
    raise ConnectionError("fallo")


def test_three_states_full_cycle():
    clock = FakeClock()
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10, clock=clock)
    assert cb.state is CircuitState.CLOSED

    for _ in range(2):
        with pytest.raises(ConnectionError):
            cb.call(boom)
    assert cb.state is CircuitState.OPEN

    with pytest.raises(ExternalServiceUnavailable):   # bloquea sin llamar
        cb.call(lambda: "no debería ejecutarse")

    clock.t = 11
    assert cb.state is CircuitState.HALF_OPEN

    assert cb.call(lambda: "ok") == "ok"              # prueba exitosa -> cierra
    assert cb.state is CircuitState.CLOSED


def test_half_open_failure_reopens():
    clock = FakeClock()
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=5, clock=clock)
    with pytest.raises(ConnectionError):
        cb.call(boom)
    clock.t = 6
    assert cb.state is CircuitState.HALF_OPEN
    with pytest.raises(ConnectionError):
        cb.call(boom)
    assert cb.state is CircuitState.OPEN


def test_retry_exponential_backoff_delays():
    delays, calls = [], {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 4:
            raise ConnectionError("x")
        return "ok"

    result = retry_with_backoff(flaky, max_attempts=4, base_delay=0.5, jitter=False, sleep=delays.append)
    assert result == "ok"
    assert delays == [0.5, 1.0, 2.0]


def test_retry_gives_up_and_raises():
    with pytest.raises(ConnectionError):
        retry_with_backoff(boom, max_attempts=3, jitter=False, sleep=lambda s: None)
