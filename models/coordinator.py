from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Coordinator(Base):

    __tablename__ = "coordinador"

    coordinator_id: Mapped[int] = mapped_column(
        "id_coordinador",
        primary_key=True,
        autoincrement=True
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

    status: Mapped[bool] = mapped_column(
        "estado",
        Boolean,
        nullable=False,
        default=True
    )