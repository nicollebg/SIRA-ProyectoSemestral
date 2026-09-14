from datetime import datetime

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Student(Base):

    __tablename__ = "estudiante"

    student_id: Mapped[int] = mapped_column(
        "id_estudiante",
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

    email: Mapped[str] = mapped_column(
        "correo",
        String(100),
        nullable=False
    )

    password: Mapped[str] = mapped_column(
        "contraseña",
        String(255),
        nullable=False
    )

    registration_date: Mapped[datetime] = mapped_column(
        "fechaRegistro",
        DateTime,
        nullable=False
    )

    status: Mapped[bool] = mapped_column(
        "estado",
        Boolean,
        nullable=False,
        default=True
    )

    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="student"
    )

    waitlists: Mapped[list["Waitlist"]] = relationship(
        back_populates="student"
    )

    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="student"
    )