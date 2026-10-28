from domain.group import GroupSnapshot
from domain.ports import GroupReader


class CatalogService:
    """Caso de uso: consultar el catálogo. Dependencia inyectada por constructor."""

    def __init__(self, group_reader: GroupReader):
        self._groups = group_reader

    def available_groups(self, text_filter: str = "") -> list[GroupSnapshot]:
        return [g for g in self._groups.list_groups(text_filter) if g.has_capacity]

    def all_groups(self, text_filter: str = "") -> list[GroupSnapshot]:
        return self._groups.list_groups(text_filter)
