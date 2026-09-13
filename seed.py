"""
seed.py
Carga los datos iniciales (grupos y usuarios de prueba) la primera vez
que se ejecuta la aplicación, para que quede lista para usar de inmediato.
"""

from security import hash_password
from models import Grupo, Usuario

GRUPOS_INICIALES = [
    # materia, grupo, docente, horario, cupos_totales, cupos_ocupados
    ("Bases de Datos II", "A", "M. Rojas", "Lun/Mié 8:00-10:00", 30, 12),
    ("Ingeniería de Software", "B", "C. Peña", "Mar/Jue 10:00-12:00", 30, 27),
    ("Redes de Computadores", "A", "L. Gómez", "Vie 7:00-11:00", 30, 30),
    ("Estructuras de Datos", "C", "A. Torres", "Lun/Mié 14:00-16:00", 30, 12),
    ("Sistemas Operativos", "A", "J. Ibarra", "Mar/Jue 16:00-18:00", 30, 30),
]

# Credenciales de prueba (se muestran también en el README)
USUARIOS_INICIALES = [
    # correo, password, nombre, rol
    ("nbarrera@umb.edu.co", "estudiante123", "Nicolle Barrera", "estudiante"),
    ("mquesada@umb.edu.co", "estudiante123", "Mateo Quesada", "estudiante"),
    ("dcardenas@umb.edu.co", "estudiante123", "Diana Cardenas", "estudiante"),
    ("cpena@umb.edu.co", "coordinador123", "C. Peña", "coordinador"),
]


def seed_if_empty(session_factory):
    """Inserta datos de ejemplo solo si las tablas están vacías (no duplica en reinicios)."""
    with session_factory() as session:
        if session.query(Grupo).count() == 0:
            for materia, grupo, docente, horario, total, ocupados in GRUPOS_INICIALES:
                session.add(Grupo(
                    materia=materia, grupo=grupo, docente=docente, horario=horario,
                    cupos_totales=total, cupos_ocupados=ocupados,
                ))

        if session.query(Usuario).count() == 0:
            for correo, password, nombre, rol in USUARIOS_INICIALES:
                session.add(Usuario(
                    correo=correo, password_hash=hash_password(password),
                    nombre=nombre, rol=rol,
                ))

        session.commit()
