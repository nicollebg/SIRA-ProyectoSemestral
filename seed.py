"""
seed.py

Carga los datos iniciales de SIRA.
"""

from datetime import datetime

from sqlalchemy import select

from database import SessionLocal

from models import (
    Student,
    Teacher,
    Subject,
    Group,
)

from security import hash_password


# ============================================================
# DOCENTES Y MATERIAS
# ============================================================

MATERIAS = [

    (
        "BD2",
        "Bases de Datos II",
        4,
        "M.",
        "Rojas"
    ),

    (
        "IS1",
        "Ingeniería de Software",
        4,
        "C.",
        "Peña"
    ),

    (
        "RC1",
        "Redes de Computadores",
        4,
        "L.",
        "Gómez"
    ),

    (
        "ED1",
        "Estructuras de Datos",
        3,
        "A.",
        "Torres"
    ),

    (
        "SO1",
        "Sistemas Operativos",
        4,
        "J.",
        "Ibarra"
    ),
]


# ============================================================
# GRUPOS
# ============================================================

GRUPOS = [

    (
        0,
        "A",
        "Lun/Mié 8:00-10:00",
        30,
        12
    ),

    (
        1,
        "B",
        "Mar/Jue 10:00-12:00",
        30,
        27
    ),

    (
        2,
        "A",
        "Vie 7:00-11:00",
        30,
        30
    ),

    (
        3,
        "C",
        "Lun/Mié 14:00-16:00",
        30,
        12
    ),

    (
        4,
        "A",
        "Mar/Jue 16:00-18:00",
        30,
        30
    ),
]


# ============================================================
# USUARIOS
# ============================================================

USUARIOS = [

    (
        "NB-001",
        "Nicolle Barrera",
        "nbarrera@umb.edu.co",
        "estudiante123"
    ),

    (
        "MQ-002",
        "Mateo Quesada",
        "mquesada@umb.edu.co",
        "estudiante123"
    ),

    (
        "DC-003",
        "Diana Cardenas",
        "dcardenas@umb.edu.co",
        "estudiante123"
    ),

    (
        "COORD-001",
        "C. Peña",
        "cpena@umb.edu.co",
        "coordinador123"
    ),
]


# ============================================================
# SEED
# ============================================================

def seed_if_empty(
    session_factory=SessionLocal
):

    with session_factory() as session:

        # ----------------------------------------------------
        # DOCENTES
        # ----------------------------------------------------

        docentes = []

        for indice, materia in enumerate(
            MATERIAS,
            start=1
        ):

            codigo = materia[0]
            nombre_materia = materia[1]
            nombre = materia[3]
            apellido = materia[4]

            correo = (
                f"{nombre.lower()}"
                f".{apellido.lower()}"
                "@umb.edu.co"
            )

            docente = session.scalar(

                select(Teacher)

                .where(
                    Teacher.email
                    == correo
                )
            )

            if docente is None:

                docente = Teacher(

                    document=
                        f"DOC-{indice:03d}",

                    name=nombre,

                    last_name=apellido,

                    email=correo,

                    phone="",

                    status=True
                )

                session.add(
                    docente
                )

                session.flush()

            docentes.append(
                docente
            )

        # ----------------------------------------------------
        # MATERIAS
        # ----------------------------------------------------

        materias = []

        for indice, materia in enumerate(
            MATERIAS
        ):

            codigo = materia[0]
            nombre = materia[1]
            semestre = materia[2]

            subject = session.scalar(

                select(Subject)

                .where(
                    Subject.code
                    == codigo
                )

            )

            if subject is None:

                subject = Subject(

                    code=codigo,

                    name=nombre,

                    semester=semestre,

                    teacher_id=
                        docentes[indice]
                        .teacher_id,

                    status=True
                )

                session.add(
                    subject
                )

                session.flush()

            materias.append(
                subject
            )

        # ----------------------------------------------------
        # GRUPOS
        # ----------------------------------------------------

        existe_grupo = session.scalar(

            select(
                Group.group_id
            )

            .limit(1)

        )

        if existe_grupo is None:

            for (
                indice,
                nombre_grupo,
                horario,
                cupo_maximo,
                cupo_actual
            ) in GRUPOS:

                session.add(

                    Group(

                        subject_id=
                            materias[indice]
                            .subject_id,

                        academic_period=
                            "2026-2",

                        schedule=
                            horario,

                        maximum_capacity=
                            cupo_maximo,

                        current_capacity=
                            cupo_actual,

                        lock_version=0,

                        status=True
                    )
                )

        # ----------------------------------------------------
        # USUARIOS
        # ----------------------------------------------------

        for (
            codigo,
            nombre,
            correo,
            password
        ) in USUARIOS:

            usuario = session.scalar(

                select(Student)

                .where(
                    Student.email
                    == correo
                )

            )

            if usuario is None:

                usuario = Student(

                    code=codigo,

                    name=nombre,

                    email=correo,

                    password=
                        hash_password(
                            password
                        ),

                    registration_date=
                        datetime.utcnow(),

                    status=True
                )

                session.add(
                    usuario
                )

        session.commit()