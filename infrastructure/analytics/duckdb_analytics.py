"""Adaptador de análisis: DuckDB en memoria."""
import json
import os
import re
import tempfile

import duckdb

from domain.ports import AnalyticsPort

_VALID_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DuckDbAnalytics(AnalyticsPort):
    def __init__(self, database: str = ":memory:"):
        self._con = duckdb.connect(database)

    def load(self, table: str, records: list[dict]) -> int:
        if not _VALID_NAME.match(table):
            raise ValueError(f"Nombre de tabla inválido: {table}")
        if not records:
            self._con.execute(f'DROP TABLE IF EXISTS "{table}"')
            return 0
        # DuckDB lee el JSON directamente (read_json_auto infiere columnas y tipos)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(records, f)
            path = f.name
        try:
            self._con.execute(
                f'CREATE OR REPLACE TABLE "{table}" AS SELECT * FROM read_json_auto(?)', [path])
        finally:
            os.remove(path)
        return self._con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]

    def query(self, sql: str) -> list[dict]:
        cur = self._con.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def columns(self, table: str) -> list[str]:
        return [r[0] for r in self._con.execute(f'DESCRIBE "{table}"').fetchall()]
