from sqlalchemy import String, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Group(Base):

    __tablename__ = "grupo"

    group_id: Mapped[int] = mapped_column(
        "id_grupo",
        primary_key=True,
        autoincrement=True
    )

    subject_id: Mapped[int] = mapped_column(
        "id_materia",
        ForeignKey("materia.id_materia"),
        nullable=False
    )

    academic_period: Mapped[str] = mapped_column(
        "periodoAcademico",
        String(20),
        nullable=False
    )

    schedule: Mapped[str] = mapped_column(
        "horario",
        String(50),
        nullable=False
    )

    maximum_capacity: Mapped[int] = mapped_column(
        "cupoMaximo",
        Integer,
        nullable=False
    )

    current_capacity: Mapped[int] = mapped_column(
        "cupoActual",
        Integer,
        nullable=False,
        default=0
    )

    lock_version: Mapped[int] = mapped_column(
        "versionBloqueo",
        Integer,
        nullable=False,
        default=0
    )

    status: Mapped[bool] = mapped_column(
        "estado",
        Boolean,
        nullable=False,
        default=True
    )

    subject: Mapped["Subject"] = relationship(
        back_populates="groups"
    )

    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="group"
    )

    waitlists: Mapped[list["Waitlist"]] = relationship(
        back_populates="group"
    )

    performance_metrics: Mapped[list["PerformanceMetric"]] = relationship(
        back_populates="group"
    )