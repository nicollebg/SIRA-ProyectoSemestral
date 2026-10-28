"""Entidad de dominio pura: un grupo del catálogo SIRA."""
from dataclasses import dataclass


@dataclass(frozen=True)
class GroupSnapshot:
    id: int
    subject: str
    teacher: str
    schedule: str
    maximum_capacity: int
    current_capacity: int
    waiting: int = 0

    @property
    def available_seats(self) -> int:
        return max(0, self.maximum_capacity - self.current_capacity)

    @property
    def has_capacity(self) -> bool:
        return self.available_seats > 0

    @property
    def status_label(self) -> str:
        """Misma regla que usa la UI actual (Disponible / Pocos cupos / Sin cupos)."""
        if self.available_seats <= 0:
            return "Sin cupos"
        if self.available_seats <= 3:
            return "Pocos cupos"
        return "Disponible"
