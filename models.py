"""
models.py
Modelos de datos (SQLAlchemy ORM) del Sistema de Registro Académico.
Funcionan igual sobre SQLite (por defecto) o MySQL (ver database.py).
"""

from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    correo = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nombre = Column(String(150), nullable=False)
    rol = Column(String(20), nullable=False)  # 'estudiante' | 'coordinador'


class Grupo(Base):
    __tablename__ = "grupos"

    id = Column(Integer, primary_key=True)
    materia = Column(String(150), nullable=False)
    grupo = Column(String(10), nullable=False)
    docente = Column(String(150), nullable=False)
    horario = Column(String(100), nullable=False)
    cupos_totales = Column(Integer, nullable=False)
    cupos_ocupados = Column(Integer, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("materia", "grupo", name="uq_materia_grupo"),)


class Inscripcion(Base):
    __tablename__ = "inscripciones"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    grupo_id = Column(Integer, ForeignKey("grupos.id"), nullable=False, index=True)
    estado = Column(String(20), nullable=False, default="activa")  # activa | cancelada
    fecha = Column(DateTime, default=datetime.utcnow)


class ListaEspera(Base):
    __tablename__ = "lista_espera"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    grupo_id = Column(Integer, ForeignKey("grupos.id"), nullable=False, index=True)
    activo = Column(Boolean, default=True)
    fecha_ingreso = Column(DateTime, default=datetime.utcnow)


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    mensaje = Column(String(255), nullable=False)
    leida = Column(Boolean, default=False)
    fecha = Column(DateTime, default=datetime.utcnow)


class MetricaTransaccion(Base):
    """Registra cada intento de inscripción para RF-15 (tiempos, fallos, reintentos)."""
    __tablename__ = "metricas_transacciones"

    id = Column(Integer, primary_key=True)
    grupo_id = Column(Integer, ForeignKey("grupos.id"), nullable=False, index=True)
    resultado = Column(String(20), nullable=False)  # inscrito | lista_espera | fallida | ya_inscrito | ya_en_espera
    tiempo_respuesta_ms = Column(Float, nullable=False)
    reintentos = Column(Integer, default=0)
    fecha = Column(DateTime, default=datetime.utcnow)
