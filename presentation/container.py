"""
Composition root: AQUÍ (y solo aquí) se conectan puertos con adaptadores.
La UI (Streamlit) pide servicios ya armados a esta función.
"""
from application.catalog_service import CatalogService
from application.enrollment_service import EnrollmentService
from application.open_data_service import OpenDataService
from infrastructure.analytics.duckdb_analytics import DuckDbAnalytics
from infrastructure.http.resilience import CircuitBreaker
from infrastructure.http.socrata_client import SocrataClient
from infrastructure.persistence.legacy_enrollment_gateway import LegacyEnrollmentGateway
from infrastructure.persistence.sqlalchemy_group_reader import SqlAlchemyGroupReader

# Datasets reales de datos.gov.co
IES_DATASET = "n5yy-8nav"        # MEN - Instituciones de Educación Superior (SNIES)
DIVIPOLA_DATASET = "gdxc-w37w"   # DIVIPOLA - códigos de municipios (nomenclatura DANE)


def build_catalog_service(session_factory) -> CatalogService:
    return CatalogService(SqlAlchemyGroupReader(session_factory))


def build_enrollment_service(session_factory) -> EnrollmentService:
    return EnrollmentService(SqlAlchemyGroupReader(session_factory), LegacyEnrollmentGateway())


def build_open_data_service() -> tuple[OpenDataService, list[SocrataClient]]:
    ies = SocrataClient("ies_snies", IES_DATASET, CircuitBreaker(failure_threshold=3, recovery_timeout=30))
    divipola = SocrataClient("divipola_dane", DIVIPOLA_DATASET, CircuitBreaker(failure_threshold=3, recovery_timeout=30))
    clients = [ies, divipola]
    return OpenDataService(clients, DuckDbAnalytics()), clients
