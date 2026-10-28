"""
Puertos (interfaces) de la arquitectura hexagonal.
El dominio y la aplicación dependen SOLO de estas abstracciones;
infrastructure/ aporta las implementaciones (adaptadores).
"""
from abc import ABC, abstractmethod
from typing import Optional

from domain.group import GroupSnapshot


class GroupReader(ABC):
    @abstractmethod
    def list_groups(self, text_filter: str = "") -> list[GroupSnapshot]: ...

    @abstractmethod
    def get_group(self, group_id: int) -> Optional[GroupSnapshot]: ...


class EnrollmentGateway(ABC):
    @abstractmethod
    def enroll(self, student_id: int, group_id: int) -> str:
        """Devuelve: 'inscrito', 'ya_inscrito', 'lista_espera' o 'ya_en_espera'."""


class OpenDataPort(ABC):
    name: str

    @abstractmethod
    def fetch_records(self, limit: int = 1000) -> list[dict]:
        """Descarga registros JSON de una API pública."""


class AnalyticsPort(ABC):
    @abstractmethod
    def load(self, table: str, records: list[dict]) -> int: ...

    @abstractmethod
    def query(self, sql: str) -> list[dict]: ...
