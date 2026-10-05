"""
services.py
Lógica de negocio del sistema SIRA.
Compatible con los modelos SQLAlchemy actuales.
"""

import random
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import OperationalError

from database import engine, SessionLocal

from models import (
    Student,
    Teacher,
    Subject,
    Group,
    Enrollment,
    Waitlist,
    Notification,
    PerformanceMetric,
)

from security import hash_password, verify_password


MAX_REINTENTOS = 5


# ============================================================
# ERRORES
# ============================================================

class ErrorValidacion(Exception):
    """Error de validación que se muestra en la interfaz."""
    pass


class ErrorConcurrencia(Exception):
    """Error producido por demasiadas operaciones concurrentes."""
    pass


# ============================================================
# USUARIO DE SESIÓN
# ============================================================

@dataclass
class UsuarioSesion:
    """
    Objeto utilizado por app.py para conservar la sesión.
    No es una tabla de la base de datos.
    """

    id: int
    nombre: str
    correo: str
    rol: str
    password_hash: str = ""


# ============================================================
# AUTENTICACIÓN
# ============================================================

def autenticar(correo: str, password: str) -> UsuarioSesion:

    correo = (correo or "").strip().lower()
    password = password or ""

    if not correo:
        raise ErrorValidacion(
            "Ingresa tu usuario institucional."
        )

    if "@" not in correo or "." not in correo.split("@")[-1]:
        raise ErrorValidacion(
            "El usuario institucional debe ser un correo válido."
        )

    if not password:
        raise ErrorValidacion(
            "Ingresa tu contraseña."
        )

    with SessionLocal() as session:

        usuario = session.scalar(
            select(Student).where(
                Student.email == correo
            )
        )

        if usuario is None:
            raise ErrorValidacion(
                "Usuario o contraseña incorrectos."
            )

        if not verify_password(
            password,
            usuario.password
        ):
            raise ErrorValidacion(
                "Usuario o contraseña incorrectos."
            )

        if not usuario.status:
            raise ErrorValidacion(
                "El usuario está inactivo."
            )

        # Los coordinadores de prueba tienen código COORD-...
        if (usuario.code or "").startswith("COORD-"):
            rol = "coordinador"
        else:
            rol = "estudiante"

        return UsuarioSesion(
            id=usuario.student_id,
            nombre=usuario.name,
            correo=usuario.email,
            rol=rol,
            password_hash=usuario.password,
        )


# ============================================================
# CATÁLOGO
# ============================================================

def _fila_grupo(
    grupo: Group,
    espera: int = 0
) -> dict:

    if grupo.subject:

        materia = grupo.subject.name

    else:

        materia = "Materia sin nombre"

    docente = "Sin docente"

    if grupo.subject and grupo.subject.teacher:

        docente = (
            f"{grupo.subject.teacher.name} "
            f"{grupo.subject.teacher.last_name}"
        ).strip()

    disponibles = max(
        0,
        grupo.maximum_capacity - grupo.current_capacity
    )

    if disponibles <= 0:

        estado = "Sin cupos"
        estado_coordinador = "Lleno"

    elif disponibles <= 3:

        estado = "Pocos cupos"
        estado_coordinador = "Casi lleno"

    else:

        estado = "Disponible"
        estado_coordinador = "Normal"

    return {
        "id": grupo.group_id,
        "materia": materia,
        "grupo": grupo.group_id,
        "docente": docente,
        "horario": grupo.schedule,
        "cupos_totales": grupo.maximum_capacity,
        "cupos_ocupados": grupo.current_capacity,
        "cupos_disponibles": disponibles,
        "en_espera": espera,
        "estado": estado,
        "estado_coordinador": estado_coordinador,
    }


def listar_grupos(
    filtro_texto: str = ""
) -> list[dict]:

    with SessionLocal() as session:

        grupos = session.scalars(
            select(Group)
            .order_by(
                Group.subject_id,
                Group.group_id
            )
        ).all()

        resultado = []

        for grupo in grupos:

            materia = (
                grupo.subject.name
                if grupo.subject
                else ""
            )

            if (
                filtro_texto
                and filtro_texto.lower()
                not in materia.lower()
            ):
                continue

            espera = session.scalar(
                select(
                    func.count(
                        Waitlist.waitlist_id
                    )
                ).where(
                    Waitlist.group_id == grupo.group_id,
                    Waitlist.status.is_(True)
                )
            ) or 0

            resultado.append(
                _fila_grupo(
                    grupo,
                    espera
                )
            )

        return resultado


def obtener_grupo(
    grupo_id: int
) -> Optional[dict]:

    with SessionLocal() as session:

        grupo = session.get(
            Group,
            grupo_id
        )

        if grupo is None:
            return None

        espera = session.scalar(
            select(
                func.count(
                    Waitlist.waitlist_id
                )
            ).where(
                Waitlist.group_id == grupo_id,
                Waitlist.status.is_(True)
            )
        ) or 0

        return _fila_grupo(
            grupo,
            espera
        )


# ============================================================
# TRANSACCIONES
# ============================================================

def _iniciar_transaccion_exclusiva(conn):

    if engine.dialect.name == "sqlite":

        conn.exec_driver_sql(
            "BEGIN IMMEDIATE"
        )

    else:

        conn.exec_driver_sql(
            "START TRANSACTION"
        )


def _leer_grupo_bloqueado(
    conn,
    grupo_id: int
):

    consulta = (
        select(
            Group.group_id,
            Group.maximum_capacity,
            Group.current_capacity
        )
        .where(
            Group.group_id == grupo_id
        )
    )

    if engine.dialect.name != "sqlite":

        consulta = consulta.with_for_update()

    fila = conn.execute(
        consulta
    ).first()

    if fila is None:

        raise ErrorValidacion(
            "El grupo seleccionado no existe."
        )

    return fila


# ============================================================
# MÉTRICAS
# ============================================================

def _registrar_metrica(
    grupo_id: int,
    resultado: str,
    tiempo_ms: float,
    reintentos: int
):

    with SessionLocal() as session:

        session.add(
            PerformanceMetric(
                group_reference_id=grupo_id,
                event_timestamp=datetime.utcnow(),
                response_time_ms=int(tiempo_ms),
                successful_transactions=(
                    1
                    if resultado in {
                        "inscrito",
                        "ya_inscrito",
                        "lista_espera",
                        "ya_en_espera"
                    }
                    else 0
                ),
                failed_transactions=(
                    1
                    if resultado == "fallida"
                    else 0
                ),
                retried_transactions=reintentos,
            )
        )

        session.commit()


# ============================================================
# UNA INSCRIPCIÓN
# ============================================================

def _intentar_inscripcion(
    usuario_id: int,
    grupo_id: int
) -> str:

    conn = engine.connect()

    try:

        _iniciar_transaccion_exclusiva(
            conn
        )

        # ----------------------------------------------------
        # ¿YA ESTÁ INSCRITO?
        # ----------------------------------------------------

        ya_inscrito = conn.execute(

            select(
                Enrollment.enrollment_id
            )

            .where(
                Enrollment.student_id == usuario_id,
                Enrollment.group_id == grupo_id,
                Enrollment.status.is_(True)
            )

        ).first()

        if ya_inscrito:

            conn.exec_driver_sql(
                "COMMIT"
            )

            return "ya_inscrito"

        # ----------------------------------------------------
        # BLOQUEAR GRUPO
        # ----------------------------------------------------

        grupo = _leer_grupo_bloqueado(
            conn,
            grupo_id
        )

        # ----------------------------------------------------
        # HAY CUPO
        # ----------------------------------------------------

        if (
            grupo.current_capacity
            < grupo.maximum_capacity
        ):

            conn.execute(

                update(Group)

                .where(
                    Group.group_id == grupo_id
                )

                .values(
                    current_capacity=
                    Group.current_capacity + 1
                )
            )

            conn.execute(

                insert(Enrollment)

                .values(
                    student_id=usuario_id,
                    group_id=grupo_id,
                    enrollment_date=datetime.utcnow(),
                    period="2026-2",
                    status=True
                )
            )

            conn.exec_driver_sql(
                "COMMIT"
            )

            return "inscrito"

        # ----------------------------------------------------
        # ¿YA ESTÁ EN LISTA DE ESPERA?
        # ----------------------------------------------------

        ya_espera = conn.execute(

            select(
                Waitlist.waitlist_id
            )

            .where(
                Waitlist.student_id == usuario_id,
                Waitlist.group_id == grupo_id,
                Waitlist.status.is_(True)
            )

        ).first()

        if ya_espera:

            conn.exec_driver_sql(
                "COMMIT"
            )

            return "ya_en_espera"

        # ----------------------------------------------------
        # NUEVA POSICIÓN
        # ----------------------------------------------------

        posicion = conn.execute(

            select(
                func.count(
                    Waitlist.waitlist_id
                )
            )

            .where(
                Waitlist.group_id == grupo_id,
                Waitlist.status.is_(True)
            )

        ).scalar_one() + 1

        conn.execute(

            insert(Waitlist)

            .values(
                student_id=usuario_id,
                group_id=grupo_id,
                position=posicion,
                entry_date=datetime.utcnow(),
                status=True
            )
        )

        conn.exec_driver_sql(
            "COMMIT"
        )

        return "lista_espera"

    except Exception:

        try:

            conn.exec_driver_sql(
                "ROLLBACK"
            )

        except Exception:
            pass

        raise

    finally:

        conn.close()


# ============================================================
# INSCRIBIR ESTUDIANTE
# ============================================================

def inscribir_estudiante(
    usuario_id: int,
    grupo_id: int
) -> str:

    inicio = time.time()
    reintentos = 0

    while True:

        try:

            resultado = _intentar_inscripcion(
                usuario_id,
                grupo_id
            )

            tiempo_ms = (
                time.time() - inicio
            ) * 1000

            _registrar_metrica(
                grupo_id,
                resultado,
                tiempo_ms,
                reintentos
            )

            return resultado

        except OperationalError as exc:

            texto = str(exc).lower()

            bloqueado = any(
                palabra in texto
                for palabra in [
                    "locked",
                    "deadlock",
                    "lock wait timeout"
                ]
            )

            if (
                bloqueado
                and reintentos < MAX_REINTENTOS
            ):

                reintentos += 1

                time.sleep(
                    random.uniform(
                        0.02,
                        0.08
                    ) * reintentos
                )

                continue

            tiempo_ms = (
                time.time() - inicio
            ) * 1000

            _registrar_metrica(
                grupo_id,
                "fallida",
                tiempo_ms,
                reintentos
            )

            raise ErrorConcurrencia(
                "No se pudo completar la inscripción "
                "por alta concurrencia. Intenta de nuevo."
            ) from exc


# ============================================================
# CANCELAR INSCRIPCIÓN
# ============================================================

def cancelar_inscripcion(
    usuario_id: int,
    grupo_id: int
) -> bool:

    conn = engine.connect()

    try:

        _iniciar_transaccion_exclusiva(
            conn
        )

        inscripcion = conn.execute(

            select(
                Enrollment.enrollment_id
            )

            .where(
                Enrollment.student_id == usuario_id,
                Enrollment.group_id == grupo_id,
                Enrollment.status.is_(True)
            )

        ).first()

        if not inscripcion:

            conn.exec_driver_sql(
                "COMMIT"
            )

            return False

        # ----------------------------------------------------
        # CANCELAR
        # ----------------------------------------------------

        conn.execute(

            update(Enrollment)

            .where(
                Enrollment.enrollment_id
                == inscripcion.enrollment_id
            )

            .values(
                status=False
            )
        )

        # ----------------------------------------------------
        # LIBERAR CUPO
        # ----------------------------------------------------

        conn.execute(

            update(Group)

            .where(
                Group.group_id == grupo_id
            )

            .values(
                current_capacity=
                Group.current_capacity - 1
            )
        )

        # ----------------------------------------------------
        # SIGUIENTE EN ESPERA
        # ----------------------------------------------------

        siguiente = conn.execute(

            select(
                Waitlist.waitlist_id,
                Waitlist.student_id
            )

            .where(
                Waitlist.group_id == grupo_id,
                Waitlist.status.is_(True)
            )

            .order_by(
                Waitlist.position.asc(),
                Waitlist.entry_date.asc()
            )

        ).first()

        if siguiente:

            conn.execute(

                update(Waitlist)

                .where(
                    Waitlist.waitlist_id
                    == siguiente.waitlist_id
                )

                .values(
                    status=False
                )
            )

            conn.execute(

                update(Group)

                .where(
                    Group.group_id == grupo_id
                )

                .values(
                    current_capacity=
                    Group.current_capacity + 1
                )
            )

            conn.execute(

                insert(Enrollment)

                .values(
                    student_id=siguiente.student_id,
                    group_id=grupo_id,
                    enrollment_date=datetime.utcnow(),
                    period="2026-2",
                    status=True
                )
            )

            grupo_info = conn.execute(

                select(
                    Subject.name,
                    Group.group_id
                )

                .join(
                    Group,
                    Group.subject_id
                    == Subject.subject_id
                )

                .where(
                    Group.group_id == grupo_id
                )

            ).first()

            if grupo_info:

                mensaje = (
                    f"Se te asignó un cupo en "
                    f"{grupo_info.name} - "
                    f"Grupo {grupo_info.group_id}."
                )

            else:

                mensaje = (
                    "Se te asignó un cupo "
                    "en un grupo de tu lista de espera."
                )

            conn.execute(

                insert(Notification)

                .values(
                    student_id=siguiente.student_id,
                    message=mensaje,
                    status=True
                )
            )

        conn.exec_driver_sql(
            "COMMIT"
        )

        return True

    except Exception:

        try:

            conn.exec_driver_sql(
                "ROLLBACK"
            )

        except Exception:
            pass

        raise

    finally:

        conn.close()


# ============================================================
# MIS INSCRIPCIONES
# ============================================================

def listar_mis_inscripciones(
    usuario_id: int
) -> list[dict]:

    with SessionLocal() as session:

        filas = session.execute(

            select(
                Group.group_id,
                Subject.name.label("materia"),
                Group.group_id.label("grupo"),
                Teacher.name.label("docente"),
                Teacher.last_name.label(
                    "apellido_docente"
                ),
                Group.schedule.label(
                    "horario"
                )
            )

            .join(
                Enrollment,
                Enrollment.group_id
                == Group.group_id
            )

            .join(
                Subject,
                Subject.subject_id
                == Group.subject_id
            )

            .outerjoin(
                Teacher,
                Teacher.teacher_id
                == Subject.teacher_id
            )

            .where(
                Enrollment.student_id
                == usuario_id,

                Enrollment.status.is_(True)
            )

            .order_by(
                Subject.name
            )

        ).all()

        resultado = []

        for fila in filas:

            docente = fila.docente or "Sin docente"

            if fila.apellido_docente:

                docente = (
                    f"{docente} "
                    f"{fila.apellido_docente}"
                )

            resultado.append({

                "id": fila.group_id,

                "materia":
                    fila.materia,

                "grupo":
                    fila.grupo,

                "docente":
                    docente,

                "horario":
                    fila.horario
            })

        return resultado


# ============================================================
# LISTA DE ESPERA
# ============================================================

def listar_mi_lista_espera(
    usuario_id: int
) -> list[dict]:

    with SessionLocal() as session:

        filas = session.execute(

            select(
                Waitlist.group_id,
                Subject.name.label(
                    "materia"
                ),
                Group.group_id.label(
                    "grupo"
                ),
                Waitlist.position
            )

            .join(
                Group,
                Group.group_id
                == Waitlist.group_id
            )

            .join(
                Subject,
                Subject.subject_id
                == Group.subject_id
            )

            .where(
                Waitlist.student_id
                == usuario_id,

                Waitlist.status.is_(True)
            )

            .order_by(
                Waitlist.position.asc()
            )

        ).all()

        resultado = []

        for fila in filas:

            total = session.scalar(

                select(
                    func.count(
                        Waitlist.waitlist_id
                    )
                )

                .where(
                    Waitlist.group_id
                    == fila.group_id,

                    Waitlist.status.is_(True)
                )

            ) or 0

            resultado.append({

                "grupo_id":
                    fila.group_id,

                "materia":
                    fila.materia,

                "grupo":
                    fila.grupo,

                "posicion":
                    fila.position,

                "total_en_espera":
                    total
            })

        return resultado


def obtener_posicion_espera(
    usuario_id: int,
    grupo_id: int
) -> Optional[int]:

    with SessionLocal() as session:

        posicion = session.scalar(

            select(
                Waitlist.position
            )

            .where(

                Waitlist.student_id
                == usuario_id,

                Waitlist.group_id
                == grupo_id,

                Waitlist.status.is_(True)
            )

        )

        return posicion


# ============================================================
# NOTIFICACIONES
# ============================================================

def listar_notificaciones(
    usuario_id: int,
    limite: int = 5
) -> list[str]:

    with SessionLocal() as session:

        mensajes = session.scalars(

            select(
                Notification.message
            )

            .where(

                Notification.student_id
                == usuario_id,

                Notification.status.is_(True)
            )

            .order_by(
                Notification.notification_id.desc()
            )

            .limit(limite)

        ).all()

        return list(reversed(mensajes))


# ============================================================
# MÉTRICAS
# ============================================================

def resumen_metricas() -> dict:

    with SessionLocal() as session:

        tiempos = session.scalars(

            select(
                PerformanceMetric.response_time_ms
            )

            .where(
                PerformanceMetric
                .response_time_ms
                .is_not(None)
            )

        ).all()

        fallidas = session.scalar(

            select(
                func.sum(
                    PerformanceMetric
                    .failed_transactions
                )
            )

        ) or 0

        reintentos = session.scalar(

            select(
                func.sum(
                    PerformanceMetric
                    .retried_transactions
                )
            )

        ) or 0

        return {

            "tiempos_ms":
                list(tiempos),

            "transacciones_fallidas":
                int(fallidas),

            "reintentos":
                int(reintentos)
        }


# ============================================================
# USUARIOS PARA SIMULACIÓN
# ============================================================

def preparar_usuarios_simulados(
    cantidad: int
) -> list[int]:

    with SessionLocal() as session:

        ids = []

        for i in range(
            1,
            cantidad + 1
        ):

            correo = (
                f"sim{i}@demo.local"
            )

            usuario = session.scalar(

                select(Student)

                .where(
                    Student.email
                    == correo
                )

            )

            if usuario is None:

                usuario = Student(

                    code=f"SIM-{i}",

                    name=(
                        f"Estudiante "
                        f"Simulado {i}"
                    ),

                    email=correo,

                    password=
                        hash_password(
                            "simulacion"
                        ),

                    registration_date=
                        datetime.utcnow(),

                    status=True
                )

                session.add(
                    usuario
                )

                session.flush()

            ids.append(
                usuario.student_id
            )

        session.commit()

        return ids


# ============================================================
# REINICIAR SIMULACIÓN
# ============================================================

def reiniciar_estado_grupo_para_simulacion(
    grupo_id: int,
    usuario_ids: list[int]
) -> None:

    with SessionLocal() as session:

        inscripciones = session.scalars(

            select(Enrollment)

            .where(

                Enrollment.group_id
                == grupo_id,

                Enrollment.student_id
                .in_(usuario_ids),

                Enrollment.status.is_(True)
            )

        ).all()

        liberados = len(
            inscripciones
        )

        for inscripcion in inscripciones:

            inscripcion.status = False

        session.execute(

            update(Waitlist)

            .where(

                Waitlist.group_id
                == grupo_id,

                Waitlist.student_id
                .in_(usuario_ids),

                Waitlist.status.is_(True)
            )

            .values(
                status=False
            )
        )

        if liberados:

            grupo = session.get(
                Group,
                grupo_id
            )

            if grupo:

                grupo.current_capacity = max(
                    0,
                    grupo.current_capacity
                    - liberados
                )

        session.commit()