"""create sira tables

Revision ID: d95249f39a00
Revises: 
Create Date: 2026-09-13 21:00:31.645480

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'd95249f39a00'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Eliminar restricciones antiguas si existen
    try:
        op.drop_constraint('fk_notificacion_estudiante', 'notificacion', type_='foreignkey')
    except Exception:
        pass

    # 2. Eliminar tablas anteriores (en orden por dependencias)
    tables_to_drop = [
        'metricarendimiento', 'listaespera', 'inscripcion',
        'grupo', 'materia', 'estudiante', 'coordinador', 'programa'
    ]
    for table in tables_to_drop:
        op.execute(f"DROP TABLE IF EXISTS {table}")

    # 3. Crear tabla docente si no existe (indispensable para la Foreign Key de Materia)
    op.create_table(
        'docente',
        sa.Column('id_docente', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('documento', sa.String(length=20), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('apellido', sa.String(length=100), nullable=False),
        sa.Column('correo', sa.String(length=100), nullable=False),
        sa.Column('telefono', sa.String(length=50), nullable=False),
        sa.Column('estado', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id_docente')
    )

    # 4. Crear tablas independientes nuevas
    op.create_table(
        'Coordinador',
        sa.Column('id_coordinador', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('correo', sa.String(length=100), nullable=False),
        sa.Column('estado', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id_coordinador')
    )

    op.create_table(
        'Estudiante',
        sa.Column('id_estudiante', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('codigo', sa.String(length=20), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('correo', sa.String(length=100), nullable=False),
        sa.Column('contraseña', sa.String(length=255), nullable=False),
        sa.Column('fechaRegistro', sa.DateTime(), nullable=False),
        sa.Column('estado', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id_estudiante')
    )

    # 5. Crear Materia (ahora 'docente' ya existe)
    op.create_table(
        'Materia',
        sa.Column('id_materia', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('codigo', sa.String(length=20), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('semestre', sa.Integer(), nullable=False),
        sa.Column('id_docente', sa.Integer(), nullable=False),
        sa.Column('estado', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['id_docente'], ['docente.id_docente']),
        sa.PrimaryKeyConstraint('id_materia')
    )

    # 6. Crear Grupo
    op.create_table(
        'Grupo',
        sa.Column('id_grupo', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('id_materia', sa.Integer(), nullable=False),
        sa.Column('periodoAcademico', sa.String(length=20), nullable=False),
        sa.Column('horario', sa.String(length=50), nullable=False),
        sa.Column('cupoMaximo', sa.Integer(), nullable=False),
        sa.Column('cupoActual', sa.Integer(), nullable=False),
        sa.Column('versionBloqueo', sa.Integer(), nullable=False),
        sa.Column('estado', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['id_materia'], ['Materia.id_materia']),
        sa.PrimaryKeyConstraint('id_grupo')
    )

    # 7. Crear tablas dependientes de Estudiante y Grupo
    op.create_table(
        'Inscripcion',
        sa.Column('id_inscripcion', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('fechaInscripcion', sa.DateTime(), nullable=False),
        sa.Column('periodo', sa.String(length=100), nullable=False),
        sa.Column('estado', sa.Boolean(), nullable=False),
        sa.Column('id_estudiante', sa.Integer(), nullable=False),
        sa.Column('id_grupo', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['id_estudiante'], ['Estudiante.id_estudiante']),
        sa.ForeignKeyConstraint(['id_grupo'], ['Grupo.id_grupo']),
        sa.PrimaryKeyConstraint('id_inscripcion')
    )

    op.create_table(
        'ListaEspera',
        sa.Column('id_lista_espera', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('id_estudiante', sa.Integer(), nullable=False),
        sa.Column('id_grupo', sa.Integer(), nullable=False),
        sa.Column('posicion', sa.Integer(), nullable=False),
        sa.Column('fecha_ingreso', sa.DateTime(), nullable=False),
        sa.Column('estado', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['id_estudiante'], ['Estudiante.id_estudiante']),
        sa.ForeignKeyConstraint(['id_grupo'], ['Grupo.id_grupo']),
        sa.PrimaryKeyConstraint('id_lista_espera')
    )

    op.create_table(
        'MetricaRendimiento',
        sa.Column('id_metrica', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('id_grupo_referencia', sa.Integer(), nullable=False),
        sa.Column('timestamp_evento', sa.DateTime(), nullable=False),
        sa.Column('tiempo_respuesta_ms', sa.Integer(), nullable=False),
        sa.Column('transacciones_exitosas', sa.Integer(), nullable=False),
        sa.Column('transacciones_fallidas', sa.Integer(), nullable=False),
        sa.Column('transacciones_reintentadas', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['id_grupo_referencia'], ['Grupo.id_grupo']),
        sa.PrimaryKeyConstraint('id_metrica')
    )

    # 8. Ajustes finales en tablas existentes
    try:
        op.create_foreign_key(None, 'notificacion', 'Estudiante', ['id_estudiante'], ['id_estudiante'])
        op.drop_column('notificacion', 'creadoPor')
    except Exception:
        pass

def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('notificacion', sa.Column('creadoPor', mysql.VARCHAR(length=100), nullable=True))
    # WARNING: constraint name is None; this directive will fail as
    # rendered.  Add a name, or use a naming convention; see
    # https://alembic.sqlalchemy.org/en/latest/naming.html
    op.drop_constraint(None, 'notificacion', type_='foreignkey')
    op.create_foreign_key(op.f('fk_notificacion_estudiante'), 'notificacion', 'estudiante', ['id_estudiante'], ['id_estudiante'])
    op.alter_column('docente', 'telefono',
               existing_type=mysql.VARCHAR(length=50),
               nullable=True)
    op.create_table('programa',
    sa.Column('id_programa', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.PrimaryKeyConstraint('id_programa'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('coordinador',
    sa.Column('id_coordinador', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('nombre', mysql.VARCHAR(length=100), nullable=False),
    sa.Column('email', mysql.VARCHAR(length=100), nullable=False),
    sa.Column('estado', mysql.TINYINT(display_width=1), server_default=sa.text("'1'"), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id_coordinador'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('listaespera',
    sa.Column('id_lista_espera', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('id_estudiante', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('id_grupo', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('posicion', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('fecha_ingreso', mysql.DATETIME(), nullable=False),
    sa.Column('estado', mysql.TINYINT(display_width=1), server_default=sa.text("'1'"), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['id_estudiante'], ['estudiante.id_estudiante'], name=op.f('fk_lista_espera_estudiante')),
    sa.ForeignKeyConstraint(['id_grupo'], ['grupo.id_grupo'], name=op.f('fk_lista_espera_grupo')),
    sa.PrimaryKeyConstraint('id_lista_espera'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('materia',
    sa.Column('id_materia', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('codigo', mysql.VARCHAR(length=20), nullable=False),
    sa.Column('nombre', mysql.VARCHAR(length=100), nullable=False),
    sa.Column('semestre', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('id_programa', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('id_docente', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('estado', mysql.TINYINT(display_width=1), server_default=sa.text("'1'"), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['id_docente'], ['docente.id_docente'], name=op.f('fk_materia_docente')),
    sa.ForeignKeyConstraint(['id_programa'], ['programa.id_programa'], name=op.f('fk_materia_programa')),
    sa.PrimaryKeyConstraint('id_materia'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('inscripcion',
    sa.Column('id_inscripcion', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('fechaInscripcion', mysql.DATETIME(), nullable=False),
    sa.Column('periodo', mysql.VARCHAR(length=100), nullable=False),
    sa.Column('estado', mysql.TINYINT(display_width=1), server_default=sa.text("'1'"), autoincrement=False, nullable=False),
    sa.Column('id_estudiante', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('id_grupo', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['id_estudiante'], ['estudiante.id_estudiante'], name=op.f('fk_inscripcion_estudiante')),
    sa.ForeignKeyConstraint(['id_grupo'], ['grupo.id_grupo'], name=op.f('fk_inscripcion_grupo')),
    sa.PrimaryKeyConstraint('id_inscripcion'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('metricarendimiento',
    sa.Column('id_metrica', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('id_grupo_referencia', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('timestamp_evento', mysql.DATETIME(), nullable=False),
    sa.Column('tiempo_respuesta_ms', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('transacciones_exitosas', mysql.INTEGER(), server_default=sa.text("'0'"), autoincrement=False, nullable=True),
    sa.Column('transacciones_fallidas', mysql.INTEGER(), server_default=sa.text("'0'"), autoincrement=False, nullable=True),
    sa.Column('transacciones_reintentadas', mysql.INTEGER(), server_default=sa.text("'0'"), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['id_grupo_referencia'], ['grupo.id_grupo'], name=op.f('fk_metrica_grupo')),
    sa.PrimaryKeyConstraint('id_metrica'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('grupo',
    sa.Column('id_grupo', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('id_materia', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('nombreProfesor', mysql.VARCHAR(length=100), nullable=True),
    sa.Column('periodoAcademico', mysql.VARCHAR(length=20), nullable=False),
    sa.Column('horario', mysql.VARCHAR(length=50), nullable=False),
    sa.Column('cupoMaximo', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('cupoActual', mysql.INTEGER(), server_default=sa.text("'0'"), autoincrement=False, nullable=False),
    sa.Column('versionBloqueo', mysql.INTEGER(), server_default=sa.text("'0'"), autoincrement=False, nullable=False),
    sa.Column('estado', mysql.TINYINT(display_width=1), server_default=sa.text("'1'"), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['id_materia'], ['materia.id_materia'], name=op.f('fk_grupo_materia')),
    sa.PrimaryKeyConstraint('id_grupo'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('estudiante',
    sa.Column('id_estudiante', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('codigo', mysql.VARCHAR(length=20), nullable=False),
    sa.Column('nombre', mysql.VARCHAR(length=100), nullable=False),
    sa.Column('correo', mysql.VARCHAR(length=100), nullable=False),
    sa.Column('contraseña', mysql.VARCHAR(length=255), nullable=False),
    sa.Column('fechaRegistro', mysql.DATETIME(), nullable=False),
    sa.Column('estado', mysql.TINYINT(display_width=1), server_default=sa.text("'1'"), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id_estudiante'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.drop_table('MetricaRendimiento')
    op.drop_table('ListaEspera')
    op.drop_table('Inscripcion')
    op.drop_table('Grupo')
    op.drop_table('Materia')
    op.drop_table('Estudiante')
    op.drop_table('Coordinador')
    # ### end Alembic commands ###
