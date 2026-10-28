import pytest

from application.open_data_service import OpenDataService
from domain.errors import ExternalServiceUnavailable
from infrastructure.analytics.duckdb_analytics import DuckDbAnalytics
from infrastructure.http.resilience import CircuitBreaker, CircuitState
from infrastructure.http.socrata_client import SocrataClient

RECORDS = [{"departamento": "Bogotá", "valor": i} for i in range(5)] + \
          [{"departamento": "Antioquia", "valor": 10}, {"departamento": "Antioquia", "valor": 20}]


def test_duckdb_loads_json_and_runs_queries():
    db = DuckDbAnalytics()
    assert db.load("t", RECORDS) == 7
    rows = db.query('SELECT departamento, COUNT(*) AS n FROM t GROUP BY 1 ORDER BY n DESC')
    assert rows[0] == {"departamento": "Bogotá", "n": 5}


def test_service_summary_and_top_categories():
    svc = OpenDataService([], DuckDbAnalytics())
    svc._analytics.load("t", RECORDS)
    assert len(svc.summary("t")) == 2
    column, rows = svc.top_categories("t")
    assert column == "departamento" and rows[0]["total"] == 5


def test_duckdb_rejects_sql_injection_in_table_name():
    with pytest.raises(ValueError):
        DuckDbAnalytics().load('t"; DROP TABLE x;--', RECORDS)


def test_socrata_client_success_and_retry():
    calls = {"n": 0}

    def flaky_get(url, params, timeout):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("temporal")
        return RECORDS

    delays = []
    client = SocrataClient("x", "abcd-1234", http_get=flaky_get, sleep=delays.append, base_delay=0.5)
    assert len(client.fetch_records()) == 7
    assert calls["n"] == 3 and len(delays) == 2   # 2 esperas antes del éxito


def test_socrata_client_opens_breaker_after_failures():
    def always_down(url, params, timeout):
        raise ConnectionError("caída")

    client = SocrataClient("x", "abcd-1234", breaker=CircuitBreaker(failure_threshold=2),
                           http_get=always_down, sleep=lambda s: None, max_attempts=2)
    for _ in range(2):
        with pytest.raises(ExternalServiceUnavailable):
            client.fetch_records()
    assert client.breaker.state is CircuitState.OPEN
