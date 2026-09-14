from datetime import datetime

from sqlalchemy import Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class PerformanceMetric(Base):

    __tablename__ = "metricaRendimiento"

    metric_id: Mapped[int] = mapped_column(
        "id_metrica",
        primary_key=True,
        autoincrement=True
    )

    group_reference_id: Mapped[int] = mapped_column(
        "id_grupo_referencia",
        ForeignKey("grupo.id_grupo")
    )

    event_timestamp: Mapped[datetime] = mapped_column(
        "timestamp_evento",
        DateTime,
        nullable=False
    )

    response_time_ms: Mapped[int] = mapped_column(
        "tiempo_respuesta_ms",
        Integer
    )

    successful_transactions: Mapped[int] = mapped_column(
        "transacciones_exitosas",
        Integer,
        default=0
    )

    failed_transactions: Mapped[int] = mapped_column(
        "transacciones_fallidas",
        Integer,
        default=0
    )

    retried_transactions: Mapped[int] = mapped_column(
        "transacciones_reintentadas",
        Integer,
        default=0
    )

    group: Mapped["Group"] = relationship(
        back_populates="performance_metrics"
    )