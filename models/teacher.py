from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Teacher(Base):

    __tablename__ = "docente"

    teacher_id: Mapped[int] = mapped_column(
        "id_docente",
        primary_key=True,
        autoincrement=True
    )

    document: Mapped[str] = mapped_column(
        "documento",
        String(20),
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        "nombre",
        String(100),
        nullable=False
    )

    last_name: Mapped[str] = mapped_column(
        "apellido",
        String(100),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        "correo",
        String(100),
        nullable=False
    )

    phone: Mapped[str] = mapped_column(
        "telefono",
        String(50)
    )

    status: Mapped[bool] = mapped_column(
        "estado",
        Boolean,
        nullable=False,
        default=True
    )

    subjects: Mapped[list["Subject"]] = relationship(
        back_populates="teacher"
    )