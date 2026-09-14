from sqlalchemy import String, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Subject(Base):

    __tablename__ = "materia"

    subject_id: Mapped[int] = mapped_column(
        "id_materia",
        primary_key=True,
        autoincrement=True
    )

    code: Mapped[str] = mapped_column(
        "codigo",
        String(20),
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        "nombre",
        String(100),
        nullable=False
    )

    semester: Mapped[int] = mapped_column(
        "semestre",
        Integer,
        nullable=False
    )


    teacher_id: Mapped[int] = mapped_column(
        "id_docente",
        ForeignKey("docente.id_docente")
    )

    status: Mapped[bool] = mapped_column(
        "estado",
        Boolean,
        nullable=False,
        default=True
    )

    teacher: Mapped["Teacher"] = relationship(
        back_populates="subjects"
    )

    groups: Mapped[list["Group"]] = relationship(
        back_populates="subject"
    )