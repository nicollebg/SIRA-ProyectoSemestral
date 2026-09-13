"""
services.py
Toda la lógica de negocio del sistema. Cada función aquí es la que
"hace funcionar de verdad" cada botón y pantalla de la interfaz (app.py).

Puntos clave de la implementación:
- inscribir_estudiante() usa una transacción exclusiva por grupo
  (BEGIN IMMEDIATE en SQLite / SELECT ... FOR UPDATE en MySQL) para que
  dos estudiantes NUNCA puedan tomar el mismo cupo al mismo tiempo.
- Si la base de datos está ocupada por otra transacción concurrente,
  la operación se reintenta automáticamente (con backoff) hasta
  MAX_REINTENTOS veces, y cada intento se registra en las métricas.
- cancelar_inscripcion() libera el cupo y lo asigna automáticamente
  al primer estudiante de la lista de espera, generándole una notificación.
"""

import random
import time
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import OperationalError

from database import engine, SessionLocal
from models import (
    Grupo, Inscripcion, ListaEspera, MetricaTransaccion, Notificacion, Usuario,
)
from security import hash_password, verify_password

MAX_REINTENTOS = 5


class ErrorValidacion(Exception):
    """Error de validación de datos de entrada, para mostrar en la interfaz."""


class ErrorConcurrencia(Exception):
    """No se pudo completar la operación tras varios reintentos por alta concurrencia."""


# =============================================================================
# AUTENTICACIÓN (pantalla de login)
# =============================================================================

def autenticar(correo: str, password: str) -> Usuario:
    """Valida el formulario de login y verifica las credenciales contra la BD."""
    correo = (correo or "").strip().lower()
    password = password or ""

    if not correo:
        raise ErrorValidacion("Ingresa tu usuario institucional.")
    if "@" not in correo or "." not in correo.split("@")[-1]:
        raise ErrorValidacion("El usuario institucional debe ser un correo válido.")
    if not password:
        raise ErrorValidacion("Ingresa tu contraseña.")

    with SessionLocal() as session:
        usuario = session.scalar(select(Usuario).where(Usuario.correo == correo))
        if usuario is None or not verify_password(password, usuario.password_hash):
            raise ErrorValidacion("Usuario o contraseña incorrectos.")
        session.expunge(usuario)
        return usuario


# =============================================================================
# CATÁLOGO DE MATERIAS Y GRUPOS
# =============================================================================

def listar_grupos(filtro_texto: str = "") -> list[dict]:
    """Devuelve los grupos (con cupos y estado calculados) para la pantalla de catálogo."""
    with SessionLocal() as session:
        grupos = session.scalars(select(Grupo).order_by(Grupo.materia, Grupo.grupo)).all()

        conteos_espera = dict(session.execute(
            select(ListaEspera.grupo_id, func.count(ListaEspera.id))
            .where(ListaEspera.activo.is_(True))
            .group_by(ListaEspera.grupo_id)
        ).all())

        resultado = []
        for g in grupos:
            if filtro_texto and filtro_texto.lower() not in g.materia.lower():
                continue
            disponibles = g.cupos_totales - g.cupos_ocupados
            if disponibles <= 0:
                estado, estado_coordinador = "Sin cupos", "Lleno"
            elif disponibles <= 3:
                estado, estado_coordinador = "Pocos cupos", "Casi lleno"
            else:
                estado, estado_coordinador = "Disponible", "Normal"

            resultado.append({
                "id": g.id, "materia": g.materia, "grupo": g.grupo, "docente": g.docente,
                "horario": g.horario, "cupos_totales": g.cupos_totales,
                "cupos_ocupados": g.cupos_ocupados, "cupos_disponibles": disponibles,
                "en_espera": conteos_espera.get(g.id, 0),
                "estado": estado, "estado_coordinador": estado_coordinador,
            })
        return resultado


def obtener_grupo(grupo_id: int) -> Optional[dict]:
    for g in listar_grupos():
        if g["id"] == grupo_id:
            return g
    return None


# =============================================================================
# INSCRIPCIÓN (transaccional, con bloqueo de registros y reintentos)
# =============================================================================

def _iniciar_transaccion_exclusiva(conn):
    """Abre una transacción que bloquea escrituras concurrentes sobre la BD."""
    if engine.dialect.name == "sqlite":
        conn.exec_driver_sql("BEGIN IMMEDIATE")
    else:  # MySQL / MariaDB / Postgres
        conn.exec_driver_sql("START TRANSACTION")


def _leer_grupo_bloqueado(conn, grupo_id: int):
    """Lee la fila del grupo bloqueándola para evitar que otra transacción la modifique."""
    if engine.dialect.name == "sqlite":
        # SQLite ya bloqueó toda la base de datos con BEGIN IMMEDIATE.
        fila = conn.execute(
            select(Grupo.cupos_totales, Grupo.cupos_ocupados).where(Grupo.id == grupo_id)
        ).first()
    else:
        # SELECT ... FOR UPDATE: bloqueo real a nivel de fila en MySQL/Postgres.
        fila = conn.execute(
            select(Grupo.cupos_totales, Grupo.cupos_ocupados)
            .where(Grupo.id == grupo_id)
            .with_for_update()
        ).first()
    if fila is None:
        raise ErrorValidacion("El grupo seleccionado no existe.")
    return fila


def _registrar_metrica(grupo_id: int, resultado: str, tiempo_ms: float, reintentos: int):
    with SessionLocal() as session:
        session.add(MetricaTransaccion(
            grupo_id=grupo_id, resultado=resultado,
            tiempo_respuesta_ms=tiempo_ms, reintentos=reintentos,
        ))
        session.commit()


def _intentar_inscripcion(usuario_id: int, grupo_id: int) -> str:
    """Un único intento de inscripción, dentro de una transacción exclusiva."""
    conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        _iniciar_transaccion_exclusiva(conn)

        ya_inscrito = conn.execute(
            select(Inscripcion.id).where(
                Inscripcion.usuario_id == usuario_id,
                Inscripcion.grupo_id == grupo_id,
                Inscripcion.estado == "activa",
            )
        ).first()
        if ya_inscrito:
            conn.exec_driver_sql("COMMIT")
            return "ya_inscrito"

        grupo = _leer_grupo_bloqueado(conn, grupo_id)

        if grupo.cupos_ocupados < grupo.cupos_totales:
            conn.execute(
                update(Grupo).where(Grupo.id == grupo_id)
                .values(cupos_ocupados=Grupo.cupos_ocupados + 1)
            )
            conn.execute(insert(Inscripcion).values(
                usuario_id=usuario_id, grupo_id=grupo_id,
                estado="activa", fecha=datetime.utcnow(),
            ))
            conn.exec_driver_sql("COMMIT")
            return "inscrito"

        ya_en_espera = conn.execute(
            select(ListaEspera.id).where(
                ListaEspera.usuario_id == usuario_id,
                ListaEspera.grupo_id == grupo_id,
                ListaEspera.activo.is_(True),
            )
        ).first()
        if ya_en_espera:
            conn.exec_driver_sql("COMMIT")
            return "ya_en_espera"

        conn.execute(insert(ListaEspera).values(
            usuario_id=usuario_id, grupo_id=grupo_id,
            activo=True, fecha_ingreso=datetime.utcnow(),
        ))
        conn.exec_driver_sql("COMMIT")
        return "lista_espera"

    except Exception:
        conn.exec_driver_sql("ROLLBACK")
        raise
    finally:
        conn.close()


def inscribir_estudiante(usuario_id: int, grupo_id: int) -> str:
    """
    Inscribe a un estudiante en un grupo (RF-04 a RF-09).
    Reintenta automáticamente si la base de datos está bloqueada por otra
    inscripción concurrente sobre el mismo grupo (esto es lo que evita el
    sobrecupo cuando muchos estudiantes se inscriben al mismo tiempo).
    """
    inicio = time.time()
    reintentos = 0

    while True:
        try:
            resultado = _intentar_inscripcion(usuario_id, grupo_id)
            tiempo_ms = (time.time() - inicio) * 1000
            _registrar_metrica(grupo_id, resultado, tiempo_ms, reintentos)
            return resultado
        except OperationalError as exc:
            if "locked" in str(exc).lower() and reintentos < MAX_REINTENTOS:
                reintentos += 1
                time.sleep(random.uniform(0.02, 0.08) * reintentos)  # backoff simple
                continue
            tiempo_ms = (time.time() - inicio) * 1000
            _registrar_metrica(grupo_id, "fallida", tiempo_ms, reintentos)
            raise ErrorConcurrencia(
                "No se pudo completar la inscripción por alta concurrencia. Intenta de nuevo."
            ) from exc


def cancelar_inscripcion(usuario_id: int, grupo_id: int) -> bool:
    """
    Cancela una inscripción (RF-11) y asigna el cupo liberado al primer
    estudiante de la lista de espera (RF-12), notificándolo (RF-13).
    """
    conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        _iniciar_transaccion_exclusiva(conn)

        inscripcion = conn.execute(
            select(Inscripcion.id).where(
                Inscripcion.usuario_id == usuario_id,
                Inscripcion.grupo_id == grupo_id,
                Inscripcion.estado == "activa",
            )
        ).first()
        if not inscripcion:
            conn.exec_driver_sql("COMMIT")
            return False

        conn.execute(
            update(Inscripcion).where(Inscripcion.id == inscripcion.id).values(estado="cancelada")
        )
        conn.execute(
            update(Grupo).where(Grupo.id == grupo_id)
            .values(cupos_ocupados=Grupo.cupos_ocupados - 1)
        )

        siguiente = conn.execute(
            select(ListaEspera.id, ListaEspera.usuario_id)
            .where(ListaEspera.grupo_id == grupo_id, ListaEspera.activo.is_(True))
            .order_by(ListaEspera.fecha_ingreso.asc())
        ).first()

        if siguiente:
            conn.execute(
                update(ListaEspera).where(ListaEspera.id == siguiente.id).values(activo=False)
            )
            conn.execute(
                update(Grupo).where(Grupo.id == grupo_id)
                .values(cupos_ocupados=Grupo.cupos_ocupados + 1)
            )
            conn.execute(insert(Inscripcion).values(
                usuario_id=siguiente.usuario_id, grupo_id=grupo_id,
                estado="activa", fecha=datetime.utcnow(),
            ))
            grupo_info = conn.execute(
                select(Grupo.materia, Grupo.grupo).where(Grupo.id == grupo_id)
            ).first()
            conn.execute(insert(Notificacion).values(
                usuario_id=siguiente.usuario_id,
                mensaje=f"Se te asignó un cupo en {grupo_info.materia} - Grupo {grupo_info.grupo}.",
                leida=False, fecha=datetime.utcnow(),
            ))

        conn.exec_driver_sql("COMMIT")
        return True
    except Exception:
        conn.exec_driver_sql("ROLLBACK")
        raise
    finally:
        conn.close()


# =============================================================================
# CONSULTAS DEL ESTUDIANTE (pantalla "Mis inscripciones y lista de espera")
# =============================================================================

def listar_mis_inscripciones(usuario_id: int) -> list[dict]:
    with SessionLocal() as session:
        filas = session.execute(
            select(Grupo.id, Grupo.materia, Grupo.grupo, Grupo.docente, Grupo.horario)
            .join(Inscripcion, Inscripcion.grupo_id == Grupo.id)
            .where(Inscripcion.usuario_id == usuario_id, Inscripcion.estado == "activa")
            .order_by(Grupo.materia)
        ).all()
        return [dict(f._mapping) for f in filas]


def listar_mi_lista_espera(usuario_id: int) -> list[dict]:
    with SessionLocal() as session:
        grupos_en_espera = session.execute(
            select(ListaEspera.grupo_id, ListaEspera.fecha_ingreso)
            .where(ListaEspera.usuario_id == usuario_id, ListaEspera.activo.is_(True))
        ).all()

        resultado = []
        for grupo_id, fecha_ingreso in grupos_en_espera:
            grupo = session.get(Grupo, grupo_id)
            total_espera = session.scalar(
                select(func.count(ListaEspera.id))
                .where(ListaEspera.grupo_id == grupo_id, ListaEspera.activo.is_(True))
            )
            anteriores = session.scalar(
                select(func.count(ListaEspera.id)).where(
                    ListaEspera.grupo_id == grupo_id,
                    ListaEspera.activo.is_(True),
                    ListaEspera.fecha_ingreso < fecha_ingreso,
                )
            )
            resultado.append({
                "grupo_id": grupo_id, "materia": grupo.materia, "grupo": grupo.grupo,
                "posicion": anteriores + 1, "total_en_espera": total_espera,
            })
        return resultado


def obtener_posicion_espera(usuario_id: int, grupo_id: int) -> Optional[int]:
    for item in listar_mi_lista_espera(usuario_id):
        if item["grupo_id"] == grupo_id:
            return item["posicion"]
    return None


def listar_notificaciones(usuario_id: int, limite: int = 5) -> list[str]:
    with SessionLocal() as session:
        mensajes = session.scalars(
            select(Notificacion.mensaje)
            .where(Notificacion.usuario_id == usuario_id)
            .order_by(Notificacion.fecha.desc())
            .limit(limite)
        ).all()
        return list(reversed(mensajes))


# =============================================================================
# PANEL DEL COORDINADOR (métricas y ocupación en tiempo real)
# =============================================================================

def resumen_metricas() -> dict:
    with SessionLocal() as session:
        tiempos = session.scalars(select(MetricaTransaccion.tiempo_respuesta_ms)).all()
        fallidas = session.scalar(
            select(func.count(MetricaTransaccion.id))
            .where(MetricaTransaccion.resultado == "fallida")
        ) or 0
        reintentos = session.scalar(select(func.sum(MetricaTransaccion.reintentos))) or 0
        return {"tiempos_ms": list(tiempos), "transacciones_fallidas": fallidas, "reintentos": reintentos}


# =============================================================================
# SIMULADOR DE CONCURRENCIA
# =============================================================================

def preparar_usuarios_simulados(cantidad: int) -> list[int]:
    """Crea (si no existen) usuarios de prueba para el simulador y devuelve sus ids."""
    with SessionLocal() as session:
        ids = []
        for i in range(1, cantidad + 1):
            correo = f"sim{i}@demo.local"
            usuario = session.scalar(select(Usuario).where(Usuario.correo == correo))
            if usuario is None:
                usuario = Usuario(
                    correo=correo, password_hash=hash_password("simulacion"),
                    nombre=f"Estudiante Simulado {i}", rol="estudiante",
                )
                session.add(usuario)
                session.flush()
            ids.append(usuario.id)
        session.commit()
        return ids


def reiniciar_estado_grupo_para_simulacion(grupo_id: int, usuario_ids: list[int]) -> None:
    """
    Antes de cada corrida del simulador, libera cualquier cupo o puesto en
    lista de espera que los usuarios simulados tuvieran en ese grupo, para
    poder repetir la prueba de manera consistente.
    """
    with SessionLocal() as session:
        inscripciones = session.scalars(
            select(Inscripcion).where(
                Inscripcion.grupo_id == grupo_id,
                Inscripcion.usuario_id.in_(usuario_ids),
                Inscripcion.estado == "activa",
            )
        ).all()
        liberados = len(inscripciones)
        for insc in inscripciones:
            insc.estado = "cancelada"

        session.execute(
            delete(ListaEspera).where(
                ListaEspera.grupo_id == grupo_id,
                ListaEspera.usuario_id.in_(usuario_ids),
            )
        )

        if liberados:
            grupo = session.get(Grupo, grupo_id)
            grupo.cupos_ocupados = max(0, grupo.cupos_ocupados - liberados)

        session.commit()
