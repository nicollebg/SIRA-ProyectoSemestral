from domain.errors import ExternalServiceUnavailable
from domain.ports import AnalyticsPort, OpenDataPort


class OpenDataService:
    """
    Caso de uso: traer datos de >= 2 APIs públicas y analizarlos con DuckDB.
    Si una API falla, las demás siguen funcionando (degradación controlada).
    """

    def __init__(self, sources: list[OpenDataPort], analytics: AnalyticsPort):
        self._sources = sources
        self._analytics = analytics

    def refresh(self, limit: int = 1000) -> dict[str, dict]:
        """Devuelve {nombre_api: {'ok': bool, 'rows': int, 'error': str|None}}."""
        report = {}
        for src in self._sources:
            try:
                rows = src.fetch_records(limit)
                n = self._analytics.load(src.name, rows)
                report[src.name] = {"ok": True, "rows": n, "error": None}
            except ExternalServiceUnavailable as exc:
                report[src.name] = {"ok": False, "rows": 0, "error": str(exc)}
        return report

    def run_query(self, sql: str) -> list[dict]:
        return self._analytics.query(sql)

    def summary(self, table: str) -> list[dict]:
        """Query analítica 1: estadísticas descriptivas por columna (DuckDB SUMMARIZE)."""
        self._check(table)
        return self._analytics.query(f'SUMMARIZE "{table}"')

    def top_categories(self, table: str, top: int = 10) -> tuple[str | None, list[dict]]:
        """Query analítica 2: frecuencia de la primera columna categórica (GROUP BY)."""
        self._check(table)
        column = next(
            (c["column_name"] for c in self.summary(table)
             if c["column_type"] == "VARCHAR" and c["approx_unique"] and 2 <= c["approx_unique"] <= 60),
            None)
        if column is None:
            return None, []
        rows = self._analytics.query(
            f'SELECT "{column}" AS category, COUNT(*) AS total FROM "{table}" '
            f'GROUP BY 1 ORDER BY total DESC LIMIT {int(top)}')
        return column, rows

    @staticmethod
    def _check(table: str):
        import re
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table):
            raise ValueError("Nombre de tabla inválido")
