from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Notification(Base):

    __tablename__ = "notificacion"

    notification_id: Mapped[int] = mapped_column(
        "id_notificacion",
        primary_key=True,
        autoincrement=True
    )

    message: Mapped[str] = mapped_column(
        "mensaje",
        String(300),
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

    student: Mapped["Student"] = relationship(
        back_populates="notifications"
    )