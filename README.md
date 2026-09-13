# SIRA - Sistema de Registro Académico

Proyecto funcional completo (front-end + lógica + base de datos) para la
inscripción de materias descrita en la Actividad 3. Mantiene exactamente el
mismo diseño visual acordado (topbar azul marino, tarjetas blancas, pills de
estado en verde/ámbar/rojo, y las 5 pantallas: login, catálogo, confirmación
de inscripción, lista de espera y panel del coordinador), pero ahora cada
botón y formulario está conectado a una base de datos real.

## Estructura del proyecto

```
sira_project/
├── app.py          # Front-end (Streamlit) — la interfaz visual
├── services.py     # Lógica de negocio: login, inscripción, cancelación,
│                   #   lista de espera, métricas, simulador de concurrencia
├── models.py       # Modelos de la base de datos (SQLAlchemy ORM)
├── database.py     # Conexión a la base de datos (SQLite por defecto)
├── seed.py         # Datos iniciales (usuarios y grupos de prueba)
├── security.py     # Hash y verificación de contraseñas
├── requirements.txt
└── README.md
```

## Instalación y ejecución

```bash
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate

pip install -r requirements.txt

streamlit run app.py
```

Se abrirá automáticamente en el navegador (normalmente en
`http://localhost:8501`). La primera vez que se ejecuta, se crea el archivo
`sira.db` (SQLite) en la misma carpeta y se cargan los datos de prueba.

## Cuentas de prueba

| Correo                     | Contraseña       | Rol          |
|-----------------------------|------------------|--------------|
| nbarrera@umb.edu.co         | estudiante123    | Estudiante   |
| mquesada@umb.edu.co         | estudiante123    | Estudiante   |
| dcardenas@umb.edu.co        | estudiante123    | Estudiante   |
| cpena@umb.edu.co            | coordinador123   | Coordinador  |

## Qué hace cada pantalla (y qué requerimiento cubre)

| Pantalla | Funcionalidad real implementada |
|---|---|
| **Login** | Valida formato de correo y contraseña no vacía, y autentica contra la tabla `usuarios` con contraseñas cifradas (PBKDF2). RF-01. |
| **Catálogo de materias** | Lee los grupos desde la base de datos, calcula cupos disponibles y estado (Disponible / Pocos cupos / Sin cupos) en tiempo real, y permite buscar por nombre de materia. RF-02, RF-03. |
| **Confirmar inscripción** | Ejecuta una transacción exclusiva por grupo (ver "Cómo funciona el bloqueo de registros") que verifica cupos, bloquea el registro del grupo, y crea la inscripción o agrega a la lista de espera. RF-04 a RF-09. |
| **Mis inscripciones y lista de espera** | Consulta real de las inscripciones activas y la posición en cada lista de espera; botón "Cancelar" que ejecuta `cancelar_inscripcion()`. RF-10, RF-11. |
| **Panel del coordinador** | Consulta en tiempo real de ocupación por grupo (ocupados, disponibles, en espera) y métricas agregadas (tiempos de respuesta, transacciones fallidas, reintentos). RF-14, RF-15. |
| **Simulador de concurrencia** | Lanza N hilos reales que llaman a `inscribir_estudiante()` al mismo tiempo sobre el mismo grupo, para comprobar en vivo que nunca se asignan más cupos de los disponibles. |

## Cómo funciona el bloqueo de registros

`services.py` implementa la inscripción así:

1. Abre una **transacción exclusiva** (`BEGIN IMMEDIATE` en SQLite, o
   `SELECT ... FOR UPDATE` en MySQL) sobre la fila del grupo.
2. Verifica cupos disponibles y hace el `UPDATE`/`INSERT` correspondiente.
3. Hace `COMMIT`. Mientras esa transacción no termina, ninguna otra puede
   modificar el mismo grupo — así se evita que dos estudiantes obtengan el
   mismo cupo al mismo tiempo.
4. Si la base de datos está ocupada por otra transacción concurrente, la
   operación se **reintenta automáticamente** (hasta 5 veces, con espera
   creciente) y cada intento se registra en `metricas_transacciones`.

Esto se puede comprobar en vivo desde el **Simulador de concurrencia** del
panel del coordinador.

## Usar MySQL en lugar de SQLite

El proyecto usa SQLite por defecto para que funcione sin instalar nada
adicional, pero el documento del proyecto pide MySQL. Para usarlo:

1. Crea una base de datos en MySQL, por ejemplo `sira`.
2. Instala el driver: `pip install pymysql` (ya viene comentado en
   `requirements.txt`).
3. Define la variable de entorno antes de ejecutar la app:

   ```bash
   export DATABASE_URL="mysql+pymysql://usuario:clave@localhost/sira"
   streamlit run app.py
   ```

No es necesario cambiar nada más: `models.py` y `services.py` funcionan
igual sobre ambos motores (en MySQL, además, el bloqueo pasa a ser un
verdadero `SELECT ... FOR UPDATE` a nivel de fila).

## Reiniciar los datos

Para empezar de cero, cierra la aplicación y elimina el archivo `sira.db`
(y `sira.db-wal` / `sira.db-shm` si existen) de la carpeta del proyecto.
Al volver a ejecutar `streamlit run app.py` se recrean las tablas y los
datos de prueba.
