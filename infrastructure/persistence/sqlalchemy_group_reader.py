"""Adaptador de salida: lee grupos desde MySQL/SQLite con SQLAlchemy."""
from typing import Optional

from sqlalchemy import func, select

from domain.group import GroupSnapshot
from domain.ports import GroupReader
from models import Group, Waitlist


class SqlAlchemyGroupReader(GroupReader):
    def __init__(self, session_factory):
        self._session_factory = session_factory

    def _to_snapshot(self, session, g: Group) -> GroupSnapshot:
        teacher = "Sin docente"
        if g.subject and g.subject.teacher:
            t = g.subject.teacher
            teacher = f"{t.name} {t.last_name}".strip()
        waiting = session.scalar(
            select(func.count(Waitlist.waitlist_id)).where(
                Waitlist.group_id == g.group_id, Waitlist.status.is_(True))) or 0
        return GroupSnapshot(
            id=g.group_id,
            subject=g.subject.name if g.subject else "Materia sin nombre",
            teacher=teacher, schedule=g.schedule,
            maximum_capacity=g.maximum_capacity,
            current_capacity=g.current_capacity, waiting=waiting)

    def list_groups(self, text_filter: str = "") -> list[GroupSnapshot]:
        with self._session_factory() as session:
            groups = session.scalars(select(Group).order_by(Group.subject_id, Group.group_id)).all()
            result = [self._to_snapshot(session, g) for g in groups]
        if text_filter:
            result = [g for g in result if text_filter.lower() in g.subject.lower()]
        return result

    def get_group(self, group_id: int) -> Optional[GroupSnapshot]:
        with self._session_factory() as session:
            g = session.get(Group, group_id)
            return self._to_snapshot(session, g) if g else None
