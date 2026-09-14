from datetime import datetime

from sqlalchemy import Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Waitlist(Base):

    __tablename__ = "listaEspera"

    waitlist_id: Mapped[int] = mapped_column(
        "id_lista_espera",
        primary_key=True,
        autoincrement=True
    )

    student_id: Mapped[int] = mapped_column(
        "id_estudiante",
        ForeignKey("estudiante.id_estudiante"),
        nullable=False
    )

    group_id: Mapped[int] = mapped_column(
        "id_grupo",
        ForeignKey("grupo.id_grupo"),
        nullable=False
    )

    position: Mapped[int] = mapped_column(
        "posicion",
        Integer,
        nullable=False
    )

    entry_date: Mapped[datetime] = mapped_column(
        "fecha_ingreso",
        DateTime,
        nullable=False
    )

    status: Mapped[bool] = mapped_column(
        "estado",
        Boolean,
        nullable=False,
        default=True
    )

    student: Mapped["Student"] = relationship(
        back_populates="waitlists"
    )

    group: Mapped["Group"] = relationship(
        back_populates="waitlists"
    )