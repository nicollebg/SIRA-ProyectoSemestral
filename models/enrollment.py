from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Enrollment(Base):

    __tablename__ = "inscripcion"

    enrollment_id: Mapped[int] = mapped_column(
        "id_inscripcion",
        primary_key=True,
        autoincrement=True
    )

    enrollment_date: Mapped[datetime] = mapped_column(
        "fechaInscripcion",
        DateTime,
        nullable=False
    )

    period: Mapped[str] = mapped_column(
        "periodo",
        String(100),
        nullable=False
    )

    status: Mapped[bool] = mapped_column(
        "estado",
        Boolean,
        nullable=False,
        default=True
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

    student: Mapped["Student"] = relationship(
        back_populates="enrollments"
    )

    group: Mapped["Group"] = relationship(
        back_populates="enrollments"
    )