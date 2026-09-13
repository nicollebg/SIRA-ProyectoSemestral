"""
database.py
Configura la conexión a la base de datos.

Por defecto usa SQLite (archivo local sira.db) para que el proyecto
funcione sin instalar ni configurar nada externo.

Para usar MySQL (tal como se describe en el documento del proyecto),
define la variable de entorno DATABASE_URL antes de ejecutar la app, p. ej.:

    export DATABASE_URL="mysql+pymysql://usuario:clave@localhost/sira"

y agrega `pymysql` a requirements.txt (ya viene comentado ahí).
El resto del código (models.py, services.py) funciona igual con ambos motores.
"""

import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from models import Base
import seed

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///sira.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    # check_same_thread=False: necesario porque Streamlit y el simulador de
    # concurrencia acceden a la base de datos desde varios hilos.
    connect_args = {"check_same_thread": False, "timeout": 30}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _configurar_sqlite(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        # WAL permite lecturas concurrentes mientras hay una escritura en curso.
        cursor.execute("PRAGMA journal_mode=WAL")
        # Si dos transacciones chocan, SQLite espera hasta 5s antes de fallar.
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db():
    """Crea las tablas (si no existen) y carga los datos iniciales."""
    Base.metadata.create_all(engine)
    seed.seed_if_empty(SessionLocal)
